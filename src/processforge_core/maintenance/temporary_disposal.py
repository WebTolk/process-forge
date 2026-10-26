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


@dataclass(frozen=True)
class CleanupReceipt:
    resource_id: str
    result: str
    deleted_files: int = 0
    deleted_bytes: int = 0
    error_code: int | None = None
    configuration_errors: tuple[str, ...] = ()


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
    handle = create(str(resource.path), 0x10080, 3, None, 3, 0x00200000, None)
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
        if info.attributes & (0x400 | 0x10) or info.links != 1:
            raise ValueError("unsafe_path")
        disposition = wintypes.BOOL(True)
        if not dispose(
            handle, 4, ctypes.byref(disposition), ctypes.sizeof(disposition)
        ):
            raise ctypes.WinError(ctypes.get_last_error())
        return (info.size_high << 32) | info.size_low
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

    def receipt(result: str, **values: int) -> CleanupReceipt:
        return CleanupReceipt(
            resource.resource_id,
            result,
            configuration_errors=configuration_errors,
            **values,
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
