"""Explicit project-bound immutable object I/O for a trusted host boundary.

The host must exclude concurrent directory redirection and object mutation.
Portable pathname checks here do not replace host locking or a sandbox.
authorize binds the exact reference operation, including its private sibling
staging and parent creation. A digest alone never authorizes an operation.
"""

from __future__ import annotations

import hashlib
import os
import stat
import tempfile
from collections.abc import Callable, Iterable
from contextlib import nullcontext
from pathlib import Path, PurePosixPath
from typing import Literal, Protocol

from .compact_model import CompactError, ObjectRef


class _DescriptorStream(Protocol):
    """Structural descriptor access shared by streams and temp wrappers."""

    def fileno(self) -> int: ...


class _StagedStream(_DescriptorStream, Protocol):
    """The one owned, seekable staging descriptor; never reopened on Windows."""

    def seek(self, offset: int) -> int: ...

    def read(self, size: int = -1) -> bytes: ...


_CHUNK = 64 * 1024
_JSON_CODECS = {"pf.context-fragment.v1", "pf.context-manifest.v1"}
_DEVICES = {"CON", "PRN", "AUX", "NUL"} | {
    f"{prefix}{number}" for prefix in ("COM", "LPT") for number in range(1, 10)
}


def object_relative_path(ref: ObjectRef) -> PurePosixPath:
    """Compute the sole supported project-relative digest locator."""
    if type(ref) is not ObjectRef:
        raise CompactError("invalid_reference")
    return PurePosixPath(
        ".pf", "objects", "sha256", ref.digest[:2], ref.digest[2:4], ref.digest
    )


def _metadata(ref: ObjectRef) -> None:
    if type(ref) is not ObjectRef:
        raise CompactError("invalid_reference")
    if ref.codec == "raw.v1":
        return
    if ref.codec not in _JSON_CODECS or ref.media_type != "application/json":
        raise CompactError("unsupported_codec")


def _signature(info: os.stat_result) -> tuple[int, int, int, int, int]:
    return (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns)


def _redirect(info: os.stat_result) -> bool:
    return stat.S_ISLNK(info.st_mode) or bool(
        getattr(info, "st_file_attributes", 0)
        & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
    )


class ProjectObjectStore:
    """No I/O at construction, no discovery, no implicit durability backend.

    sync_directory must raise when the host cannot guarantee durability.
    A callback returning normally is a host assertion, not proof supplied by
    this class. read/verify require an exact current read grant; metadata-only
    access must not bind this body-reading store to a body reference.
    """

    def __init__(
        self,
        project_root: Path,
        *,
        authorize: Callable[[str, Literal["read", "write_artifact"]], None],
        sync_directory: Callable[[Path], None],
    ) -> None:
        root = Path(project_root)
        if not root.is_absolute() or root.drive.startswith(("\\\\?\\", "\\\\.\\")):
            raise CompactError("unsafe_project_root")
        for part in root.parts[1:]:
            if (
                part in (".", "..")
                or ":" in part
                or "\x00" in part
                or part.endswith((" ", "."))
                or part.split(".", 1)[0].upper() in _DEVICES
            ):
                raise CompactError("unsafe_project_root")
        if not callable(authorize) or not callable(sync_directory):
            raise CompactError("capability_unavailable")
        self._root = root
        self._authorize = authorize
        self._sync_directory = sync_directory

    def _sync(self, directory: Path) -> None:
        result = self._sync_directory(directory)
        if result is not None:
            raise CompactError("durability_invalid")

    def _path(self, ref: ObjectRef, action: Literal["read", "write_artifact"]) -> Path:
        _metadata(ref)
        relative = object_relative_path(ref)
        # Authorization precedes lstat, existence checks, reads and writes.
        granted = self._authorize(relative.as_posix(), action)
        if granted is not None:
            raise CompactError("authorization_invalid")
        return self._root.joinpath(*relative.parts)

    def _safe(self, path: Path, *, missing: bool = False) -> os.stat_result | None:
        if not path.is_relative_to(self._root):
            raise CompactError("unsafe_object_path")
        for candidate in reversed((path, *path.parents)):
            try:
                info = candidate.lstat()
            except FileNotFoundError:
                if (
                    missing
                    and candidate != self._root
                    and candidate.is_relative_to(self._root)
                ):
                    return None
                raise CompactError("object_missing") from None
            if _redirect(info):
                raise CompactError("unsafe_object_path")
            if candidate != path and not stat.S_ISDIR(info.st_mode):
                raise CompactError("unsafe_object_path")
        return info

    def _check_open(self, path: Path, stream: _DescriptorStream) -> os.stat_result:
        current = self._safe(path)
        opened = os.fstat(stream.fileno())
        if (
            current is None
            or not stat.S_ISREG(opened.st_mode)
            or not stat.S_ISREG(current.st_mode)
            or _signature(current) != _signature(opened)
        ):
            raise CompactError("object_changed")
        return opened

    def _consume(self, path: Path, ref: ObjectRef, *, keep: bool) -> bytes:
        before = self._safe(path)
        if before is None or not stat.S_ISREG(before.st_mode):
            raise CompactError("unsafe_object_path")
        if before.st_size != ref.size:
            raise CompactError("object_size_mismatch")
        flags = os.O_RDONLY | getattr(os, "O_BINARY", 0)
        flags |= getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0)
        try:
            descriptor = os.open(path, flags)
        except FileNotFoundError:
            raise CompactError("object_missing") from None
        with os.fdopen(descriptor, "rb") as stream:
            opened = self._check_open(path, stream)
            if _signature(opened) != _signature(before):
                raise CompactError("object_changed")
            digest = hashlib.sha256()
            size = 0
            body = bytearray()
            while True:
                chunk = stream.read(min(_CHUNK, ref.size - size + 1))
                if not chunk:
                    break
                size += len(chunk)
                if size > ref.size:
                    raise CompactError("object_size_mismatch")
                digest.update(chunk)
                if keep:
                    body.extend(chunk)
            if _signature(self._check_open(path, stream)) != _signature(opened):
                raise CompactError("object_changed")
            if size != ref.size:
                raise CompactError("object_size_mismatch")
            if digest.hexdigest() != ref.digest:
                raise CompactError("object_hash_mismatch")
            return bytes(body)

    def read(self, ref: ObjectRef, *, maximum_bytes: int) -> bytes:
        """Read only after an exact grant and a checked pre-allocation budget."""
        if type(maximum_bytes) is not int or maximum_bytes < 0:
            raise CompactError("invalid_size_limit")
        _metadata(ref)
        if ref.size > maximum_bytes:
            raise CompactError("size_limit")
        path = self._path(ref, "read")
        return self._consume(path, ref, keep=True)

    def verify(self, ref: ObjectRef) -> None:
        """Stream verification with a read grant; disclose no body to caller."""
        path = self._path(ref, "read")
        self._consume(path, ref, keep=False)

    def _directories(self, parent: Path) -> None:
        self._safe(self._root)
        node = self._root
        for part in parent.relative_to(self._root).parts:
            child = node / part
            info = self._safe(child, missing=True)
            if info is None:
                try:
                    child.mkdir()
                except FileExistsError:
                    pass
                info = self._safe(child)
            if info is None or not stat.S_ISDIR(info.st_mode):
                raise CompactError("unsafe_object_path")
            # Also sync existing ancestors: a prior failed attempt may have
            # created them without completing the durability protocol.
            self._sync(child)
            self._sync(node)
            node = child

    def _verify_staged(self, path: Path, stream: _StagedStream, ref: ObjectRef) -> None:
        before = self._check_open(path, stream)
        if before.st_size != ref.size:
            raise CompactError("object_size_mismatch")
        stream.seek(0)
        digest = hashlib.sha256()
        size = 0
        while True:
            chunk = stream.read(min(_CHUNK, ref.size - size + 1))
            if not chunk:
                break
            size += len(chunk)
            if size > ref.size:
                raise CompactError("object_size_mismatch")
            digest.update(chunk)
        if _signature(self._check_open(path, stream)) != _signature(before):
            raise CompactError("object_changed")
        if size != ref.size:
            raise CompactError("object_size_mismatch")
        if digest.hexdigest() != ref.digest:
            raise CompactError("object_hash_mismatch")

    def _equal(
        self,
        destination: Path,
        temporary: Path,
        ref: ObjectRef,
        staged_stream: _StagedStream | None = None,
    ) -> None:
        # A write grant alone must not reveal or verify existing content.
        authorized_write = self._path(ref, "write_artifact")
        authorized = self._path(ref, "read")
        if authorized_write != destination:
            raise CompactError("unsafe_object_path")
        if authorized != destination:
            raise CompactError("unsafe_object_path")
        self._consume(destination, ref, keep=False)
        self._safe(destination)
        self._safe(temporary)
        # O_RDWR only enables Windows fsync; existing bytes are never written.
        # No creation, truncation, replacement or permission change.
        flags = os.O_RDWR | getattr(os, "O_BINARY", 0)
        flags |= getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0)
        descriptor = os.open(destination, flags)
        with (
            os.fdopen(descriptor, "r+b") as existing,
            (
                nullcontext(staged_stream)
                if staged_stream is not None
                else temporary.open("rb")
            ) as staged,
        ):
            staged.seek(0)
            before = self._check_open(destination, existing)
            staged_before = self._check_open(temporary, staged)
            remaining = ref.size
            while remaining:
                count = min(_CHUNK, remaining)
                left, right = existing.read(count), staged.read(count)
                if len(left) != count or left != right:
                    raise CompactError("object_collision")
                remaining -= count
            if existing.read(1) or staged.read(1):
                raise CompactError("object_collision")
            if _signature(before) != _signature(
                self._check_open(destination, existing)
            ) or _signature(staged_before) != _signature(
                self._check_open(temporary, staged)
            ):
                raise CompactError("object_changed")
            # Reuse must establish file durability even after an uncertain
            # previous publication. Unsupported fsync is a real failure.
            os.fsync(existing.fileno())

    def publish(self, ref: ObjectRef, chunks: Iterable[bytes]) -> None:
        """Stream to a sibling, fsync, verify, link without replacement, sync.

        Failures after linking leave the orphan in place. Retrying requires
        verified byte equality and directory durability; no object is deleted.
        """
        destination = self._path(ref, "write_artifact")
        self._directories(destination.parent)
        self._safe(destination, missing=True)
        temporary: Path | None = None
        owned: tuple[int, int] | None = None
        primary: BaseException | None = None
        publication = "not_linked"
        try:
            with tempfile.NamedTemporaryFile(
                dir=destination.parent,
                prefix=".compact-",
                suffix=".tmp",
                delete=os.name == "nt",
            ) as stream:
                try:
                    temporary = Path(stream.name)
                    info = self._check_open(temporary, stream)
                    owned = (info.st_dev, info.st_ino)
                    digest = hashlib.sha256()
                    size = 0
                    for chunk in chunks:
                        if type(chunk) is not bytes:
                            raise CompactError("invalid_bytes")
                        if size + len(chunk) > ref.size:
                            raise CompactError("object_size_mismatch")
                        written = stream.write(chunk)
                        if type(written) is not int or written != len(chunk):
                            raise CompactError("short_write")
                        size += len(chunk)
                        digest.update(chunk)
                    if size != ref.size:
                        raise CompactError("object_size_mismatch")
                    if digest.hexdigest() != ref.digest:
                        raise CompactError("object_hash_mismatch")
                    stream.flush()
                    os.fsync(stream.fileno())
                    if os.name == "nt":
                        self._verify_staged(temporary, stream, ref)
                        self._path(ref, "write_artifact")
                        self._safe(destination, missing=True)
                        try:
                            os.link(temporary, destination)
                            publication = "linked"
                        except FileExistsError:
                            self._equal(destination, temporary, ref, stream)
                            publication = "existing_verified"
                        self._sync(destination.parent)
                except BaseException as exc:
                    primary = exc
                    raise
            if os.name != "nt":
                self._consume(temporary, ref, keep=False)
                self._path(ref, "write_artifact")
                self._safe(destination, missing=True)
                try:
                    os.link(temporary, destination)
                    publication = "linked"
                except FileExistsError:
                    self._equal(destination, temporary, ref)
                    publication = "existing_verified"
                self._sync(destination.parent)
        except BaseException as exc:
            if primary is not None and exc is not primary:
                BaseException.add_note(
                    primary,
                    f"object stream close failed; staging={temporary}; "
                    f"publication={publication}; "
                    f"cleanup={type(exc).__name__}: {exc}",
                )
                raise primary
            primary = exc
            raise
        finally:
            if temporary is not None and owned is not None:
                cleanup_step = "verify_owned"
                try:
                    if os.name == "nt":
                        # The context manager made its sole close attempt. Never
                        # retry a stale descriptor or unlink an unknown alias.
                        cleanup_step = "kernel_close"
                        if temporary.exists():
                            raise CompactError("staging_cleanup_pending")
                    else:
                        cleanup_info = self._safe(temporary)
                        if (
                            cleanup_info is None
                            or (cleanup_info.st_dev, cleanup_info.st_ino) != owned
                        ):
                            raise CompactError("temporary_changed")
                        cleanup_step = "unlink"
                        temporary.unlink()
                    cleanup_step = "sync_directory"
                    self._sync(temporary.parent)
                except BaseException as cleanup:
                    note = (
                        f"object staging cleanup failed; staging={temporary}; "
                        f"step={cleanup_step}; publication={publication}; "
                        f"cleanup={type(cleanup).__name__}: {cleanup}"
                    )
                    if primary is not None:
                        BaseException.add_note(primary, note)
                    else:
                        BaseException.add_note(cleanup, note)
                        raise
