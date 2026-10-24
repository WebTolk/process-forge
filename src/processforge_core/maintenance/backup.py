"""Create, verify and exclusively restore portable SQLite backup bundles.

SQLiteBackupService uses SQLite's online backup API for live sources. A bundle
contains exactly database.sqlite3 and manifest.json; its checksums detect damage,
not the authenticity of a bundle whose database and manifest were both replaced.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import sqlite3
import stat
import time
from collections.abc import Iterator
from contextlib import closing, contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO

from processforge_core.database import DatabaseFactory, SQLiteDriver
from processforge_core.maintenance.contracts import JsonObject, MaintenanceError

_DATABASE = "database.sqlite3"
_MANIFEST = "manifest.json"
_FORMAT = "processforge-sqlite-backup"
_CHUNK = 1024 * 1024
_MANIFEST_LIMIT = 65536
_WINDOWS_DEVICES = frozenset(
    {"CON", "PRN", "AUX", "NUL", "CONIN$", "CONOUT$"}
    | {f"{prefix}{number}" for prefix in ("COM", "LPT") for number in "123456789¹²³"}
)


@dataclass(frozen=True)
class _Deadline:
    end: float

    def check(self) -> None:
        if time.monotonic() >= self.end:
            raise MaintenanceError("backup_timeout")


def _identity(info: os.stat_result) -> tuple[int, int]:
    return info.st_dev, info.st_ino


def _signature(info: os.stat_result) -> tuple[int, int, int, int, int]:
    return (*_identity(info), info.st_size, info.st_mtime_ns, info.st_ctime_ns)


def _safe_path(path: Path) -> Path:
    """Reject links/reparse points before normalizing an explicit local path."""
    path = Path(path)
    parts = path.parts[1:] if path.anchor else path.parts
    for part in parts:
        if part == ".." or ":" in part or "\x00" in part:
            raise MaintenanceError("backup_unsafe_path")
        if os.name == "nt" and (
            part.endswith((" ", "."))
            or part.split(".", 1)[0].upper() in _WINDOWS_DEVICES
        ):
            raise MaintenanceError("backup_unsafe_path")
    if path.drive.startswith(("\\\\?\\", "\\\\.\\")):
        raise MaintenanceError("backup_unsafe_path")
    path = path.absolute()
    for candidate in reversed((path, *path.parents)):
        try:
            info = candidate.lstat()
        except FileNotFoundError:
            continue
        if stat.S_ISLNK(info.st_mode) or (
            getattr(info, "st_file_attributes", 0)
            & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
        ):
            raise MaintenanceError("backup_unsafe_path")
    return path


def _directory(path: Path) -> tuple[int, int]:
    info = _safe_path(path).stat()
    if not stat.S_ISDIR(info.st_mode):
        raise MaintenanceError("backup_unsafe_path")
    return _identity(info)


def _check_directory(path: Path, identity: tuple[int, int]) -> None:
    if _directory(path) != identity:
        raise MaintenanceError("backup_path_changed")


@dataclass(frozen=True)
class _File:
    path: Path
    stream: BinaryIO
    identity: tuple[int, int]

    def check(self) -> os.stat_result:
        info = os.fstat(self.stream.fileno())
        current = _safe_path(self.path).stat()
        if (
            not stat.S_ISREG(info.st_mode)
            or not stat.S_ISREG(current.st_mode)
            or _identity(info) != self.identity
            or _identity(current) != self.identity
        ):
            raise MaintenanceError("backup_path_changed")
        return info


@contextmanager
def _open_file(path: Path, *, create: bool = False) -> Iterator[_File]:
    path = _safe_path(path)
    if not create and not stat.S_ISREG(path.stat().st_mode):
        raise MaintenanceError("backup_unsafe_path")
    flags = os.O_RDWR | os.O_CREAT | os.O_EXCL if create else os.O_RDONLY
    flags |= getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)
    flags |= getattr(os, "O_NONBLOCK", 0)
    descriptor = os.open(path, flags, 0o600)
    identity = _identity(os.fstat(descriptor))
    try:
        with os.fdopen(descriptor, "r+b" if create else "rb") as stream:
            opened = _File(path, stream, identity)
            opened.check()
            yield opened
    except BaseException:
        if create:
            try:
                _remove_owned(path, identity)
            except (OSError, MaintenanceError):
                raise MaintenanceError("backup_cleanup_failed") from None
        raise


@dataclass(frozen=True)
class _Digest:
    sha256: str
    size: int
    signature: tuple[int, int, int, int, int]


def _digest(file: _File, deadline: _Deadline) -> _Digest:
    before = file.check()
    if before.st_nlink != 1:
        raise MaintenanceError("backup_unsafe_path")
    file.stream.seek(0)
    digest = hashlib.sha256()
    size = 0
    while True:
        deadline.check()
        chunk = file.stream.read(_CHUNK)
        if not chunk:
            break
        digest.update(chunk)
        size += len(chunk)
    after = file.check()
    if _signature(before) != _signature(after) or size != after.st_size:
        raise MaintenanceError("backup_changed")
    return _Digest(digest.hexdigest(), size, _signature(after))


def _sidecars(path: Path, *, absent: bool = False) -> None:
    for suffix in ("-wal", "-shm", "-journal"):
        member = _safe_path(path.with_name(path.name + suffix))
        try:
            info = member.stat()
        except FileNotFoundError:
            continue
        if absent or not stat.S_ISREG(info.st_mode):
            raise MaintenanceError("backup_unsafe_sidecar")


def _connect(
    path: Path,
    deadline: _Deadline,
    *,
    writable: bool = False,
    immutable: bool = False,
    driver: SQLiteDriver | None = None,
) -> sqlite3.Connection:
    deadline.check()
    query = "?mode=rw" if writable else "?mode=ro"
    if immutable:
        query += "&immutable=1"
    connection = (
        driver if driver is not None else DatabaseFactory.resolve_driver()
    )._connect(path.as_uri() + query, uri=True, timeout=0.05)
    try:
        connection.execute("PRAGMA trusted_schema = OFF")
        if not writable:
            connection.execute("PRAGMA query_only = ON")
        connection.set_progress_handler(
            lambda: int(time.monotonic() >= deadline.end), 1000
        )
    except BaseException:
        connection.close()
        raise
    return connection


def _integrity(
    path: Path, deadline: _Deadline, driver: SQLiteDriver | None = None
) -> JsonObject:
    with closing(
        (
            _connect(path, deadline, immutable=True)
            if driver is None
            else _connect(path, deadline, immutable=True, driver=driver)
        )
    ) as connection:
        rows = connection.execute("PRAGMA integrity_check").fetchmany(2)
        deadline.check()
        if rows != [("ok",)]:
            raise MaintenanceError("backup_integrity_failed")
        return {
            name: connection.execute("PRAGMA " + name).fetchone()[0]
            for name in ("application_id", "user_version", "page_count", "page_size")
        }


def _backup(
    source: Path, target: Path, deadline: _Deadline, driver: SQLiteDriver | None = None
) -> None:
    with closing(
        (
            _connect(source, deadline)
            if driver is None
            else _connect(source, deadline, driver=driver)
        )
    ) as reader:
        # Pin a read transaction so continuous WAL writers cannot restart the
        # backup forever. Later commits belong to the next snapshot.
        reader.execute("BEGIN")
        reader.execute("SELECT name FROM sqlite_schema LIMIT 1").fetchone()
        with closing(
            (
                _connect(target, deadline, writable=True)
                if driver is None
                else _connect(target, deadline, writable=True, driver=driver)
            )
        ) as writer:
            writer.execute("PRAGMA journal_mode = DELETE")

            def progress(status: int, remaining: int, total: int) -> None:
                deadline.check()

            reader.backup(writer, pages=128, progress=progress, sleep=0.01)
            deadline.check()
            writer.execute("PRAGMA journal_mode = DELETE")


def _unique_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise MaintenanceError("backup_manifest_invalid")
        result[key] = value
    return result


def _reject_constant(value: str) -> object:
    raise MaintenanceError("backup_manifest_invalid")


def _manifest(file: _File, deadline: _Deadline) -> JsonObject:
    if file.check().st_size > _MANIFEST_LIMIT:
        raise MaintenanceError("backup_manifest_invalid")
    deadline.check()
    file.stream.seek(0)
    try:
        document = json.loads(
            file.stream.read(_MANIFEST_LIMIT + 1).decode("utf-8"),
            object_pairs_hook=_unique_object,
            parse_constant=_reject_constant,
        )
    except (ValueError, UnicodeError, RecursionError):
        raise MaintenanceError("backup_manifest_invalid") from None
    if not isinstance(document, dict) or set(document) != {
        "schema_version",
        "format",
        "database",
        "integrity_check",
        "sqlite",
    }:
        raise MaintenanceError("backup_manifest_invalid")
    if (
        type(document["schema_version"]) is not int
        or document["schema_version"] != 1
        or document["format"] != _FORMAT
        or document["integrity_check"] != "ok"
    ):
        raise MaintenanceError("backup_manifest_invalid")
    member = document["database"]
    if not isinstance(member, dict) or set(member) != {"path", "size", "sha256"}:
        raise MaintenanceError("backup_manifest_invalid")
    digest = member["sha256"]
    if (
        member["path"] != _DATABASE
        or type(member["size"]) is not int
        or member["size"] < 100
        or not isinstance(digest, str)
        or len(digest) != 64
        or any(character not in "0123456789abcdef" for character in digest)
    ):
        raise MaintenanceError("backup_manifest_invalid")
    facts = document["sqlite"]
    if (
        not isinstance(facts, dict)
        or set(facts) != {"application_id", "user_version", "page_count", "page_size"}
        or any(type(value) is not int for value in facts.values())
    ):
        raise MaintenanceError("backup_manifest_invalid")
    return document


def _members(bundle: Path, identity: tuple[int, int], deadline: _Deadline) -> None:
    _check_directory(bundle, identity)
    names: set[str] = set()
    with os.scandir(bundle) as entries:
        for entry in entries:
            deadline.check()
            if entry.name not in {_DATABASE, _MANIFEST}:
                raise MaintenanceError("backup_members_invalid")
            names.add(entry.name)
    if names != {_DATABASE, _MANIFEST}:
        raise MaintenanceError("backup_members_invalid")


@dataclass(frozen=True)
class _Verified:
    database: _File
    manifest: _File
    database_digest: _Digest
    manifest_digest: _Digest
    facts: JsonObject
    bundle: Path
    directory_identity: tuple[int, int]

    def recheck(self, deadline: _Deadline) -> None:
        _members(self.bundle, self.directory_identity, deadline)
        if (
            _digest(self.database, deadline) != self.database_digest
            or _digest(self.manifest, deadline) != self.manifest_digest
        ):
            raise MaintenanceError("backup_changed")

    def report(self, operation: str) -> JsonObject:
        return {
            "status": "ok",
            "operation": operation,
            "verified": True,
            "bundle": str(self.bundle),
            "database": str(self.database.path),
            "sha256": self.database_digest.sha256,
            "size": self.database_digest.size,
            "manifest_sha256": self.manifest_digest.sha256,
            "schema_version": 1,
            "integrity_check": "ok",
            "sqlite": self.facts,
        }


@contextmanager
def _verified(
    bundle: Path, deadline: _Deadline, driver: SQLiteDriver | None = None
) -> Iterator[_Verified]:
    bundle = _safe_path(bundle)
    identity = _directory(bundle)
    _members(bundle, identity, deadline)
    with _open_file(bundle / _MANIFEST) as manifest:
        if manifest.check().st_size > _MANIFEST_LIMIT:
            raise MaintenanceError("backup_manifest_invalid")
        manifest_digest = _digest(manifest, deadline)
        document = _manifest(manifest, deadline)
        with _open_file(bundle / _DATABASE) as database:
            database_digest = _digest(database, deadline)
            if (
                database_digest.sha256 != document["database"]["sha256"]
                or database_digest.size != document["database"]["size"]
            ):
                raise MaintenanceError("backup_hash_mismatch")
            facts = (
                _integrity(database.path, deadline)
                if driver is None
                else _integrity(database.path, deadline, driver)
            )
            if facts != document["sqlite"]:
                raise MaintenanceError("backup_metadata_mismatch")
            verified = _Verified(
                database,
                manifest,
                database_digest,
                manifest_digest,
                facts,
                bundle,
                identity,
            )
            verified.recheck(deadline)
            yield verified


def _remove_owned(path: Path, identity: tuple[int, int]) -> None:
    try:
        info = _safe_path(path).stat()
    except FileNotFoundError:
        return
    if _identity(info) != identity or not stat.S_ISREG(info.st_mode):
        raise MaintenanceError("backup_cleanup_failed")
    path.unlink()


class SQLiteBackupService:
    """Own verified single-database backups and restore without overwriting.

    Each call has its own connections and deadline. Constructors do no I/O.
    Parent directories must already exist; unexpected symlinks, reparse points,
    sidecars in bundles and hard-linked bundle members are refused.
    Live-source read-only connections use SQLite's normal WAL/SHM coordination;
    SQLite may create these sidecars even though database contents are read-only.
    """

    def __init__(
        self, *, timeout: float = 10.0, driver: SQLiteDriver | None = None
    ) -> None:
        """Set a positive finite per-operation timeout in seconds."""
        if not math.isfinite(timeout) or timeout <= 0:
            raise ValueError("backup_timeout_invalid")
        self._timeout = timeout
        self._driver = driver

    def create(self, source: Path, bundle: Path) -> JsonObject:
        """Create a new bundle with a consistent read-only SQLite snapshot.

        Args:
            source: Existing local SQLite database, including its committed WAL.
            bundle: New bundle directory in an existing parent directory.

        Returns:
            JSON-compatible hashes, integrity facts and bundle member locations.

        Raises:
            MaintenanceError: Unsafe input, an existing output or failed backup.
        """
        deadline = _Deadline(time.monotonic() + self._timeout)
        created: list[tuple[Path, tuple[int, int]]] = []
        directory_identity: tuple[int, int] | None = None
        try:
            source, bundle = _safe_path(source), _safe_path(bundle)
            _directory(bundle.parent)
            with _open_file(source) as original:
                _sidecars(source)
                original.stream.seek(0)
                if original.stream.read(16) != b"SQLite format 3\x00":
                    raise MaintenanceError("backup_source_invalid")
                # Windows 3.13+ gives 0700 a special owner-only ACL. Inherit
                # the operator directory ACL there, including restricted tokens.
                bundle.mkdir(mode=0o777 if os.name == "nt" else 0o700)
                directory_identity = _directory(bundle)
                with _open_file(bundle / _DATABASE, create=True) as database:
                    created.append((database.path, database.identity))
                    (
                        _backup(source, database.path, deadline)
                        if self._driver is None
                        else _backup(source, database.path, deadline, self._driver)
                    )
                    original.check()
                    _sidecars(source)
                    _check_directory(bundle, directory_identity)
                    facts = (
                        _integrity(database.path, deadline)
                        if self._driver is None
                        else _integrity(database.path, deadline, self._driver)
                    )
                    digest = _digest(database, deadline)
                    document: JsonObject = {
                        "schema_version": 1,
                        "format": _FORMAT,
                        "database": {
                            "path": _DATABASE,
                            "size": digest.size,
                            "sha256": digest.sha256,
                        },
                        "integrity_check": "ok",
                        "sqlite": facts,
                    }
                    with _open_file(bundle / _MANIFEST, create=True) as manifest:
                        created.append((manifest.path, manifest.identity))
                        manifest.stream.write(
                            (
                                json.dumps(document, sort_keys=True, allow_nan=False)
                                + "\n"
                            ).encode("utf-8")
                        )
                        manifest.stream.flush()
                        os.fsync(manifest.stream.fileno())
                    os.fsync(database.stream.fileno())
                with (
                    _verified(bundle, deadline)
                    if self._driver is None
                    else _verified(bundle, deadline, self._driver)
                ) as verified:
                    return verified.report("backup")
        except BaseException as exc:
            if directory_identity is not None:
                try:
                    _check_directory(bundle, directory_identity)
                    for path, identity in reversed(created):
                        _remove_owned(path, identity)
                    bundle.rmdir()
                except (OSError, MaintenanceError):
                    raise MaintenanceError("backup_cleanup_failed") from None
            self._raise_failure(exc, deadline)
            raise

    def verify(self, bundle: Path) -> JsonObject:
        """Check schema, containment, stable SHA256 and SQLite integrity.

        Args:
            bundle: Existing bundle containing exactly the two regular members.

        Returns:
            JSON-compatible verified hashes and database metadata.

        Raises:
            MaintenanceError: Missing, unsafe, damaged, changing or invalid input.
        """
        deadline = _Deadline(time.monotonic() + self._timeout)
        try:
            with (
                _verified(bundle, deadline)
                if self._driver is None
                else _verified(bundle, deadline, self._driver)
            ) as verified:
                return verified.report("verify")
        except (OSError, sqlite3.Error) as exc:
            self._raise_failure(exc, deadline)
            raise

    def restore(self, bundle: Path, destination: Path) -> JsonObject:
        """Verify a bundle and copy its exact database into a new destination.

        Args:
            bundle: Verified input bundle, retained unchanged after restoration.
            destination: Absent file in an existing directory, outside the bundle.

        Returns:
            JSON-compatible verified hashes, destination and integrity facts.

        Raises:
            MaintenanceError: Existing/unsafe output, tampering or failed restore.
        """
        deadline = _Deadline(time.monotonic() + self._timeout)
        created: tuple[Path, tuple[int, int]] | None = None
        try:
            with (
                _verified(bundle, deadline)
                if self._driver is None
                else _verified(bundle, deadline, self._driver)
            ) as verified:
                destination = _safe_path(destination)
                parent_identity = _directory(destination.parent)
                if destination.is_relative_to(verified.bundle):
                    raise MaintenanceError("backup_unsafe_path")
                _sidecars(destination, absent=True)
                with _open_file(destination, create=True) as target:
                    created = (target.path, target.identity)
                    verified.database.stream.seek(0)
                    while True:
                        deadline.check()
                        chunk = verified.database.stream.read(_CHUNK)
                        if not chunk:
                            break
                        target.stream.write(chunk)
                    target.stream.flush()
                    os.fsync(target.stream.fileno())
                    digest = _digest(target, deadline)
                    if (
                        digest.sha256 != verified.database_digest.sha256
                        or digest.size != verified.database_digest.size
                    ):
                        raise MaintenanceError("backup_hash_mismatch")
                    if (
                        _integrity(target.path, deadline)
                        if self._driver is None
                        else _integrity(target.path, deadline, self._driver)
                    ) != verified.facts:
                        raise MaintenanceError("backup_metadata_mismatch")
                    if _digest(target, deadline) != digest:
                        raise MaintenanceError("backup_changed")
                    verified.recheck(deadline)
                    _check_directory(destination.parent, parent_identity)
                    _sidecars(destination, absent=True)
                    result = verified.report("restore")
                    result["destination"] = str(destination)
                    return result
        except BaseException as exc:
            if created is not None:
                try:
                    _check_directory(destination.parent, parent_identity)
                    _remove_owned(*created)
                except (OSError, MaintenanceError):
                    raise MaintenanceError("backup_cleanup_failed") from None
            self._raise_failure(exc, deadline)
            raise

    @staticmethod
    def _raise_failure(exc: BaseException, deadline: _Deadline) -> None:
        if isinstance(exc, MaintenanceError):
            raise exc
        if isinstance(exc, FileExistsError):
            raise MaintenanceError("backup_output_exists") from None
        if isinstance(exc, FileNotFoundError):
            raise MaintenanceError("backup_path_missing") from None
        if isinstance(exc, sqlite3.Error):
            deadline.check()
            raise MaintenanceError("backup_sqlite_failed") from None
        if isinstance(exc, OSError):
            raise MaintenanceError("backup_io_failed") from None
