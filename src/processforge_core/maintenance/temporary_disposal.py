"""Producer-owned atomic staging; no discovery, adoption or configuration I/O."""

from __future__ import annotations

import os
import stat
import uuid
from contextlib import ExitStack, contextmanager
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Iterator

from ..configuration.models import TemporaryFilesConfig
from .temporary_files import _directory, _linked

_CREATED = object()


@dataclass(frozen=True)
class TemporaryUse:
    released: bool = False
    consumers: int = 0
    evidence_finalized: bool = False


@dataclass(frozen=True)
class OwnedTemporary:
    resource_id: str
    path: Path
    identity: tuple[int, int]
    boundary: Path
    use: TemporaryUse
    _creation: object
    kind: str = "file"


@dataclass(frozen=True)
class CleanupReceipt:
    resource_id: str
    result: str
    deleted_files: int = 0
    deleted_bytes: int = 0
    error_code: int | None = None
    configuration_errors: tuple[str, ...] = ()
    deleted_directories: int = 0
    residuals: tuple[str, ...] = ()
    complete: bool = True
    reason_code: str = ""


class CleanupError(OSError):
    """An exact owned resource remains; do not hide successful-action cleanup."""


@contextmanager
def _parent(path: Path) -> Iterator[int | None]:
    """Pin every ancestor, refusing links and unsupported safe primitives."""
    with ExitStack() as stack:
        descriptor = None
        for parent in reversed(path.parents):
            descriptor = stack.enter_context(_directory(parent, descriptor))
        yield descriptor


def create_owned_file(destination: Path) -> OwnedTemporary:
    """Exclusively create one sibling staging file, never adopt an old path."""
    destination = Path(destination).absolute()
    resource_id = uuid.uuid4().hex
    path = destination.with_name(f".{destination.name}.{resource_id}.tmp")
    with _parent(path) as descriptor:
        fd = os.open(
            path if descriptor is None else path.name,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0),
            0o666,
            dir_fd=descriptor,
        )
        try:
            info = os.fstat(fd)
        finally:
            os.close(fd)
    return OwnedTemporary(
        resource_id,
        path,
        (info.st_dev, info.st_ino),
        destination.parent,
        TemporaryUse(),
        _CREATED,
    )


def create_owned_directory(boundary: Path, *, private: bool = False) -> OwnedTemporary:
    """Create one exclusive disposable child; existing directories are never adopted."""
    boundary = Path(boundary).absolute()
    resource_id = uuid.uuid4().hex
    path = boundary / ("pf-scratch-" + resource_id)
    with _parent(path) as descriptor:
        if private and os.name == "nt":
            import ctypes
            from ctypes import wintypes

            from ..egress.contracts import EgressError
            from ..egress.windows import apis, current_sid

            # Match the existing private-directory DACL at creation, but keep
            # this producer's exclusive-create rule even for a private collision.
            class Attributes(ctypes.Structure):
                _fields_ = [
                    ("length", wintypes.DWORD),
                    ("descriptor", ctypes.c_void_p),
                    ("inherit", wintypes.BOOL),
                ]

            kernel, adv = apis()
            security = ctypes.c_void_p()
            sid = current_sid()
            if not adv.ConvertStringSecurityDescriptorToSecurityDescriptorW(
                f"O:{sid}D:P(A;OICI;FA;;;{sid})",
                1,
                ctypes.byref(security),
                None,
            ):
                raise EgressError("private_acl_unavailable")
            try:
                attributes = Attributes(ctypes.sizeof(Attributes), security, False)
                if not kernel.CreateDirectoryW(str(path), ctypes.byref(attributes)):
                    error = ctypes.get_last_error()
                    if error == 183:
                        raise FileExistsError(17, "File exists", str(path))
                    raise EgressError("private_acl_unavailable")
            finally:
                kernel.LocalFree(security)
        else:
            os.mkdir(
                path if descriptor is None else path.name,
                mode=0o777 if os.name == "nt" else 0o700,
                dir_fd=descriptor,
            )
        info = path.lstat()
    return OwnedTemporary(
        resource_id,
        path,
        (info.st_dev, info.st_ino),
        boundary,
        TemporaryUse(),
        _CREATED,
        "directory",
    )


def release_owned(resource: OwnedTemporary) -> OwnedTemporary:
    """The producer has closed its consumers and finalized required evidence."""
    return replace(resource, use=TemporaryUse(True, 0, True))


def _windows_delete(resource: OwnedTemporary) -> int:
    """Delete the checked object by handle while its ancestry is pinned."""
    import ctypes
    from ctypes import wintypes

    class Information(ctypes.Structure):
        _fields_ = [
            ("attributes", wintypes.DWORD),
            ("created", wintypes.FILETIME),
            ("accessed", wintypes.FILETIME),
            ("written", wintypes.FILETIME),
            ("volume", wintypes.DWORD),
            ("size_high", wintypes.DWORD),
            ("size_low", wintypes.DWORD),
            ("links", wintypes.DWORD),
            ("index_high", wintypes.DWORD),
            ("index_low", wintypes.DWORD),
        ]

    class FileId(ctypes.Structure):
        _fields_ = [
            ("volume", ctypes.c_ulonglong),
            ("identity", ctypes.c_ubyte * 16),
        ]

    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    create = kernel.CreateFileW
    create.argtypes = [
        wintypes.LPCWSTR,
        wintypes.DWORD,
        wintypes.DWORD,
        ctypes.c_void_p,
        wintypes.DWORD,
        wintypes.DWORD,
        wintypes.HANDLE,
    ]
    create.restype = wintypes.HANDLE
    query = kernel.GetFileInformationByHandle
    query.argtypes = [wintypes.HANDLE, ctypes.POINTER(Information)]
    query.restype = wintypes.BOOL
    query_id = kernel.GetFileInformationByHandleEx
    query_id.argtypes = [
        wintypes.HANDLE,
        ctypes.c_int,
        ctypes.c_void_p,
        wintypes.DWORD,
    ]
    query_id.restype = wintypes.BOOL
    dispose = kernel.SetFileInformationByHandle
    dispose.argtypes = [
        wintypes.HANDLE,
        ctypes.c_int,
        ctypes.c_void_p,
        wintypes.DWORD,
    ]
    dispose.restype = wintypes.BOOL
    close = kernel.CloseHandle
    close.argtypes, close.restype = [wintypes.HANDLE], wintypes.BOOL
    # DELETE | READ_ATTRIBUTES, no delete sharing; OPEN_REPARSE_POINT.
    handle = create(str(resource.path), 0x10080, 3, None, 3, 0x02200000, None)
    if handle == wintypes.HANDLE(-1).value:
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        info = Information()
        if not query(handle, ctypes.byref(info)):
            raise ctypes.WinError(ctypes.get_last_error())
        file_id = FileId()
        if not query_id(handle, 18, ctypes.byref(file_id), ctypes.sizeof(file_id)):
            raise ctypes.WinError(ctypes.get_last_error())
        identity = (file_id.volume, int.from_bytes(bytes(file_id.identity), "little"))
        if identity != resource.identity:
            raise ValueError("identity_changed")
        directory = resource.kind == "directory"
        if (
            info.attributes & 0x400
            or bool(info.attributes & 0x10) != directory
            or (not directory and info.links != 1)
        ):
            raise ValueError("unsafe_path")
        disposition = wintypes.BOOL(True)
        if not dispose(
            handle, 4, ctypes.byref(disposition), ctypes.sizeof(disposition)
        ):
            raise ctypes.WinError(ctypes.get_last_error())
        return 0 if directory else (info.size_high << 32) | info.size_low
    finally:
        close(handle)


def dispose_owned(
    resource: OwnedTemporary,
    *,
    config: TemporaryFilesConfig = TemporaryFilesConfig(),
    configuration_errors: tuple[str, ...] = (),
) -> CleanupReceipt:
    """Dispose one released file; permission does not grant filesystem rights.

    Only an error-free exact boolean true permits retention. Atomic publishers
    may always discard staging, even when retaining other unused payload.
    POSIX requires an exclusively owned producer namespace: dir_fd anchors the
    boundary but cannot exclude a hostile same-user mutation of the entry.
    """

    def receipt(
        result: str,
        *,
        deleted_files: int = 0,
        deleted_bytes: int = 0,
        error_code: int | None = None,
    ) -> CleanupReceipt:
        return CleanupReceipt(
            resource.resource_id,
            result,
            deleted_files,
            deleted_bytes,
            error_code,
            configuration_errors,
        )

    if resource._creation is not _CREATED:
        return receipt("ownership_unknown")
    if (
        not resource.use.released
        or resource.use.consumers
        or not resource.use.evidence_finalized
    ):
        return receipt("needed")
    if not configuration_errors and config.retain_unused is True:
        return receipt("retained_by_configuration")
    path = resource.path
    if (
        not path.is_absolute()
        or path.parent != resource.boundary
        or path == resource.boundary
    ):
        return receipt("unsafe_path")
    try:
        with _parent(path) as descriptor:
            try:
                info = os.stat(
                    path if descriptor is None else path.name,
                    dir_fd=descriptor,
                    follow_symlinks=False,
                )
            except FileNotFoundError:
                return receipt("already_absent")
            if resource.kind == "directory":
                return _dispose_directory(resource, configuration_errors)
            if _linked(info) or not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
                return receipt("unsafe_path")
            if (info.st_dev, info.st_ino) != resource.identity:
                return receipt("identity_changed")
            if os.name == "nt":
                size = _windows_delete(resource)
            else:
                os.unlink(path.name, dir_fd=descriptor)
                size = info.st_size
            return receipt("deleted", deleted_files=1, deleted_bytes=size)
    except ValueError as error:
        return receipt(str(error))
    except OSError as error:
        return receipt(
            "cleanup_pending",
            error_code=getattr(error, "winerror", None) or error.errno or 0,
        )


def _dispose_directory(
    resource: OwnedTemporary, errors: tuple[str, ...]
) -> CleanupReceipt:
    """Walk only this created namespace, pin ancestry, refuse links and bound work."""
    files = size = directories = entries = 0
    residuals: list[str] = []
    result = "deleted"
    error_code = None
    reason_code = ""

    def walk(owned: OwnedTemporary, depth: int) -> None:
        nonlocal files, size, directories, entries
        if depth > 32 or entries >= 10000:
            raise ValueError("entry_limit")
        with _parent(owned.path) as parent:
            info = owned.path.lstat()
            if _linked(info) or not stat.S_ISDIR(info.st_mode):
                raise ValueError("unsafe_path")
            if (info.st_dev, info.st_ino) != owned.identity:
                raise ValueError("identity_changed")
            with _directory(owned.path, parent) as descriptor:
                with os.scandir(
                    descriptor if descriptor is not None else owned.path
                ) as children:
                    for child in children:
                        entries += 1
                        if entries > 10000:
                            raise ValueError("entry_limit")
                        # Windows DirEntry.stat can omit dev/inode. Query the actual
                        # entry while the producer namespace is pinned.
                        child_info = os.stat(
                            owned.path / child.name
                            if descriptor is None
                            else child.name,
                            dir_fd=descriptor,
                            follow_symlinks=False,
                        )
                        if _linked(child_info):
                            raise ValueError("unsafe_path")
                        kind = (
                            "directory" if stat.S_ISDIR(child_info.st_mode) else "file"
                        )
                        nested = OwnedTemporary(
                            owned.resource_id,
                            owned.path / child.name,
                            (child_info.st_dev, child_info.st_ino),
                            owned.path,
                            TemporaryUse(True, 0, True),
                            _CREATED,
                            kind,
                        )
                        if kind == "directory":
                            walk(nested, depth + 1)
                        else:
                            receipt = dispose_owned(nested)
                            files += receipt.deleted_files
                            size += receipt.deleted_bytes
                            if receipt.result not in {"deleted", "already_absent"}:
                                raise OSError(receipt.error_code or 0, receipt.result)
            if os.name == "nt":
                _windows_delete(owned)
            else:
                current = os.stat(owned.path.name, dir_fd=parent, follow_symlinks=False)
                if (current.st_dev, current.st_ino) != owned.identity:
                    raise ValueError("identity_changed")
                os.rmdir(owned.path.name, dir_fd=parent)
            directories += 1

    try:
        walk(resource, 0)
    except (OSError, ValueError) as error:
        result = "partial" if files or directories else "cleanup_pending"
        error_code = getattr(error, "winerror", None) or getattr(error, "errno", None)
        reason_code = str(error)[:160]
        residuals.append(str(resource.path))
    return CleanupReceipt(
        resource.resource_id,
        result,
        files,
        size,
        error_code,
        errors,
        directories,
        tuple(residuals),
        result == "deleted",
        reason_code,
    )


@contextmanager
def atomic_staging(destination: Path) -> Iterator[Path]:
    """Finalize the exact new sibling on every exit, preserving a primary error."""
    resource = create_owned_file(destination)
    primary: BaseException | None = None
    try:
        yield resource.path
    except BaseException as error:
        primary = error
        raise
    finally:
        result = dispose_owned(release_owned(resource))
        if result.result not in {"deleted", "already_absent"}:
            diagnostic = f"temporary_cleanup:{result.resource_id}:{result.result}:{result.error_code}"
            if primary is not None:
                primary.add_note(diagnostic)
            else:
                raise CleanupError(diagnostic)


@contextmanager
def owned_directory(boundary: Path) -> Iterator[Path]:
    """Finalize an exclusively created operation directory on success and failure."""
    resource = create_owned_directory(boundary)
    primary: BaseException | None = None
    try:
        yield resource.path
    except BaseException as error:
        primary = error
        raise
    finally:
        receipt = dispose_owned(release_owned(resource))
        if receipt.result not in {"deleted", "already_absent"}:
            diagnostic = f"temporary_cleanup:{resource.resource_id}:{receipt.result}:{receipt.error_code}"
            if primary is not None:
                primary.add_note(diagnostic)
            else:
                raise CleanupError(diagnostic)
