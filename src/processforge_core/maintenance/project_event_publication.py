"""Create immutable project-event migration evidence from complete bytes."""

from __future__ import annotations

import errno
import os
import stat
import tempfile
from pathlib import Path
from typing import BinaryIO


class PublicationConflict(FileExistsError):
    """An evidence name or staging entry changed or holds conflicting bytes."""


def _sync_parent(path: Path) -> None:
    if os.name != "nt":
        descriptor = os.open(path.parent, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)


def _staging_descriptor(path: Path) -> int:
    if os.name != "nt":
        return os.open(path, os.O_CREAT | os.O_EXCL | os.O_RDWR, 0o600)

    import ctypes
    import msvcrt
    from ctypes import wintypes

    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    create = kernel.CreateFileW
    create.argtypes = [
        wintypes.LPCWSTR,
        wintypes.DWORD,
        wintypes.DWORD,
        wintypes.LPVOID,
        wintypes.DWORD,
        wintypes.DWORD,
        wintypes.HANDLE,
    ]
    create.restype = wintypes.HANDLE
    read_write = 0xC0000000
    share_read_write_delete = 0x7
    create_new = 1
    normal = 0x80
    # Share deletion so the write-through move can consume this open object.
    handle = create(
        str(path), read_write, share_read_write_delete, None, create_new, normal, None
    )
    if handle == wintypes.HANDLE(-1).value:
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        return msvcrt.open_osfhandle(handle, os.O_RDWR | os.O_BINARY)
    except OSError:
        close = kernel.CloseHandle
        close.argtypes = [wintypes.HANDLE]
        close.restype = wintypes.BOOL
        close(handle)
        raise


def _open_staging(path: Path) -> BinaryIO:
    descriptor = _staging_descriptor(path)
    try:
        return os.fdopen(descriptor, "r+b")
    except BaseException:
        os.close(descriptor)
        raise


def _publish_staged(staging: Path, path: Path) -> None:
    if os.name != "nt":
        os.link(staging, path)
        return

    import ctypes
    from ctypes import wintypes

    move = ctypes.WinDLL("kernel32", use_last_error=True).MoveFileExW
    move.argtypes = [wintypes.LPCWSTR, wintypes.LPCWSTR, wintypes.DWORD]
    move.restype = wintypes.BOOL
    # Same-volume write-through rename. Neither replacement nor copy is enabled.
    movefile_write_through = 0x8
    if not move(str(staging), str(path), movefile_write_through):
        raise ctypes.WinError(ctypes.get_last_error())


def _regular(info: os.stat_result) -> bool:
    return stat.S_ISREG(info.st_mode) and not (
        getattr(info, "st_file_attributes", 0) & stat.FILE_ATTRIBUTE_REPARSE_POINT
    )


def _observed(path: Path) -> os.stat_result:
    try:
        return path.lstat()
    except FileNotFoundError as error:
        raise PublicationConflict("publication_evidence_conflict") from error


def _require_file(current: os.stat_result, expected: os.stat_result) -> None:
    if not _regular(current) or not os.path.samestat(current, expected):
        raise PublicationConflict("publication_evidence_conflict")


def _require_bytes(stream: BinaryIO, data: bytes) -> None:
    # Seeking from the end clears read-ahead before checking the actual bytes.
    if stream.seek(0, os.SEEK_END) != len(data):
        raise PublicationConflict("publication_evidence_conflict")
    stream.seek(0)
    if stream.read(len(data) + 1) != data:
        raise PublicationConflict("publication_evidence_conflict")


def _verify_open(
    path: Path, data: bytes, stream: BinaryIO, expected: os.stat_result
) -> None:
    opened = os.fstat(stream.fileno())
    _require_file(opened, expected)
    _require_file(_observed(path), opened)
    _require_bytes(stream, data)
    os.fsync(stream.fileno())
    _sync_parent(path)
    _require_bytes(stream, data)
    _require_file(_observed(path), opened)


def _open_evidence(path: Path) -> BinaryIO:
    if os.name == "nt":
        # Windows requires a writable handle to flush an existing file.
        return path.open("r+b")

    def open_readonly(name: str, flags: int) -> int:
        # An entry swapped during open must not block as a FIFO or follow a link.
        return os.open(
            name, flags | getattr(os, "O_NONBLOCK", 0) | getattr(os, "O_NOFOLLOW", 0)
        )

    return open(path, "rb", opener=open_readonly)


def _verify_existing(path: Path, data: bytes, before: os.stat_result) -> None:
    if not _regular(before):
        raise PublicationConflict("publication_evidence_conflict")

    try:
        existing = _open_evidence(path)
    except FileNotFoundError as error:
        raise PublicationConflict("publication_evidence_conflict") from error
    except OSError:
        _require_file(_observed(path), before)
        raise
    with existing:
        _verify_open(path, data, existing, before)


def _check_staging_directory(path: Path, expected: os.stat_result) -> None:
    current = _observed(path)
    if (
        not stat.S_ISDIR(current.st_mode)
        or getattr(current, "st_file_attributes", 0) & stat.FILE_ATTRIBUTE_REPARSE_POINT
        or not os.path.samestat(current, expected)
    ):
        raise PublicationConflict("publication_staging_changed")


def _remove_staging(
    staging: Path, directory: os.stat_result, owned: os.stat_result
) -> None:
    _check_staging_directory(staging.parent, directory)
    try:
        current = staging.lstat()
    except FileNotFoundError:
        return
    _require_file(current, owned)
    staging.unlink(missing_ok=True)


def _remove_staging_directory(path: Path, expected: os.stat_result) -> None:
    _check_staging_directory(path, expected)
    try:
        path.rmdir()
    except OSError as error:
        # Unexpected entries belong to someone else. Leave them in place.
        if error.errno not in {errno.ENOENT, errno.ENOTEMPTY, errno.EEXIST}:
            raise


def publish_immutable_bytes(path: Path, data: bytes) -> None:
    """Publish complete bytes once, or verify and sync an exact existing file.

    The caller provides a trusted, already durable parent and keeps final
    evidence immutable. Every writer owns a private staging directory within
    that parent. Other writers and cleanup must leave that directory alone
    while the publishing call is active. An interrupted writer can leave it
    behind. POSIX links the flushed file without clobbering and syncs the
    final directory. Windows moves it with write-through.

    Conflicting bytes or changed identity raise PublicationConflict. An I/O
    error can occur after visibility. Recover by checking the final evidence
    and retrying its exact bytes.
    """
    try:
        before = path.lstat()
    except FileNotFoundError:
        pass
    else:
        _verify_existing(path, data, before)
        return

    directory = Path(tempfile.mkdtemp(dir=path.parent, prefix=".pf-publication-"))
    directory_identity = directory.lstat()
    staging = directory / "evidence.tmp"
    primary: BaseException | None = None
    try:
        with _open_staging(staging) as stream:
            owned = os.fstat(stream.fileno())
            consumed = False
            try:
                if stream.write(data) != len(data):
                    raise OSError("publication_incomplete_write")
                stream.flush()
                os.fsync(stream.fileno())
                _require_bytes(stream, data)
                _check_staging_directory(directory, directory_identity)
                _require_file(_observed(staging), owned)

                try:
                    _publish_staged(staging, path)
                except FileExistsError:
                    _verify_existing(path, data, _observed(path))
                else:
                    consumed = os.name == "nt"
                    _verify_open(path, data, stream, owned)
            except BaseException as error:
                primary = error
                raise
            finally:
                if not consumed:
                    try:
                        _remove_staging(staging, directory_identity, owned)
                    except OSError as error:
                        if primary is None:
                            raise
                        primary.add_note(f"Publication staging cleanup failed: {error}")
    except BaseException as error:
        primary = error
        raise
    finally:
        try:
            _remove_staging_directory(directory, directory_identity)
        except OSError as error:
            if primary is None:
                raise
            primary.add_note(f"Publication staging directory cleanup failed: {error}")
