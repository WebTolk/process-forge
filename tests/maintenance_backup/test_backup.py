"""Behavior, concurrency and failure checks for real SQLite backup bundles.

These unittest cases are also collected by pytest. All databases and corruption
fixtures belong to an isolated temporary directory; no PF services are involved.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import sqlite3
import tempfile
import threading
import time
import unittest
import uuid
from collections.abc import Callable, Iterator
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing, contextmanager
from pathlib import Path
from unittest.mock import patch

from processforge_core.maintenance import backup
from processforge_core.maintenance.backup import SQLiteBackupService
from processforge_core.maintenance.contracts import MaintenanceError


class SQLiteBackupTests(unittest.TestCase):
    """Exercise the public service against operation-local databases."""

    def setUp(self) -> None:
        """Prepare isolated operator paths and an actual SQLite source."""
        # Inherit Windows ACLs. Python 3.14's owner-only TemporaryDirectory ACL
        # can exclude an otherwise authorized restricted test-process token.
        parent = Path(tempfile.gettempdir()).resolve()
        self.root = parent / ("pf-backup-test-" + uuid.uuid4().hex)
        self.root.mkdir()

        def cleanup() -> None:
            target = self.root.resolve()
            if target.parent != parent or not target.name.startswith("pf-backup-test-"):
                raise AssertionError("Unexpected test cleanup target")
            shutil.rmtree(target)

        self.addCleanup(cleanup)
        self.source = self.root / "source.sqlite3"
        self.bundle = self.root / "bundle"
        self.destination = self.root / "restored.sqlite3"
        self.service = SQLiteBackupService(timeout=3)
        with closing(sqlite3.connect(self.source)) as connection:
            connection.execute(
                "CREATE TABLE records(id INTEGER PRIMARY KEY, value TEXT)"
            )
            connection.execute("INSERT INTO records VALUES (1, 'original')")
            connection.execute("PRAGMA application_id = 1234")
            connection.execute("PRAGMA user_version = 7")
            connection.commit()

    def _contents(self, path: Path) -> list[tuple[int, str]]:
        with closing(sqlite3.connect(path.as_uri() + "?mode=ro", uri=True)) as reader:
            return reader.execute(
                "SELECT id, value FROM records ORDER BY id"
            ).fetchall()

    def _create(self) -> None:
        self.service.create(self.source, self.bundle)

    def _assert_error(self, code: str, operation: Callable[[], object]) -> None:
        with self.assertRaises(MaintenanceError) as failure:
            operation()
        self.assertEqual(failure.exception.code, code)
        self.assertEqual(str(failure.exception), code)

    def _symlink(self, target: Path, link: Path) -> None:
        try:
            link.symlink_to(target, target_is_directory=target.is_dir())
        except (OSError, NotImplementedError):
            self.skipTest("Symbolic links are unavailable for this test account")

    def test_round_trip_preserves_source_and_bundle(self) -> None:
        """Return verifiable receipts and restore exact bytes into a new file."""
        before = self.source.read_bytes()
        created = self.service.create(self.source, self.bundle)
        verified = self.service.verify(self.bundle)
        members = {item.name: item.read_bytes() for item in self.bundle.iterdir()}
        restored = self.service.restore(self.bundle, self.destination)
        self.assertEqual(created["status"], "ok")
        self.assertEqual(verified["integrity_check"], "ok")
        self.assertEqual(verified["sqlite"]["application_id"], 1234)
        self.assertEqual(verified["sqlite"]["user_version"], 7)
        self.assertEqual(created["sha256"], verified["sha256"])
        self.assertEqual(restored["sha256"], verified["sha256"])
        self.assertEqual(self.destination.read_bytes(), members["database.sqlite3"])
        self.assertEqual(
            hashlib.sha256(self.destination.read_bytes()).hexdigest(),
            restored["sha256"],
        )
        self.assertEqual(self._contents(self.destination), [(1, "original")])
        self.assertEqual(before, self.source.read_bytes())
        self.assertEqual(
            members, {p.name: p.read_bytes() for p in self.bundle.iterdir()}
        )
        self.assertEqual(set(members), {"database.sqlite3", "manifest.json"})
        json.dumps(restored, allow_nan=False)
        self.assertNotIn(str(self.source), members["manifest.json"].decode())

    def test_constructor_is_cold_and_validates_deadline(self) -> None:
        """Constructing a service must not open files or SQLite connections."""
        with patch.object(backup.sqlite3, "connect", side_effect=AssertionError):
            SQLiteBackupService()
        for value in (0.0, -1.0, float("nan"), float("inf")):
            with self.subTest(timeout=value), self.assertRaises(ValueError):
                SQLiteBackupService(timeout=value)

    def test_wal_commits_are_included_without_changing_source_bytes(self) -> None:
        """Read committed rows that exist only in the live WAL."""
        with closing(sqlite3.connect(self.source)) as writer:
            writer.execute("PRAGMA journal_mode = WAL")
            writer.execute("PRAGMA wal_checkpoint(TRUNCATE)")
            writer.execute("INSERT INTO records VALUES (2, 'wal-only')")
            writer.commit()
            wal = self.source.with_name(self.source.name + "-wal")
            self.assertGreater(wal.stat().st_size, 0)
            original, wal_bytes = self.source.read_bytes(), wal.read_bytes()
            self._create()
            self.assertEqual(
                self._contents(self.bundle / "database.sqlite3"),
                [(1, "original"), (2, "wal-only")],
            )
            self.assertEqual(original, self.source.read_bytes())
            self.assertEqual(wal_bytes, wal.read_bytes())

    def test_snapshot_stays_consistent_during_concurrent_commit(self) -> None:
        """Keep one snapshot while a WAL writer commits during native backup."""
        started, committed = threading.Event(), threading.Event()
        real_connect = backup._connect

        class ObservedConnection(sqlite3.Connection):
            def backup(
                self,
                target: sqlite3.Connection,
                *,
                pages: int = -1,
                progress: Callable[[int, int, int], object] | None = None,
                name: str = "main",
                sleep: float = 0.25,
            ) -> None:
                def observe(status: int, remaining: int, total: int) -> None:
                    started.set()
                    if not committed.wait(2):
                        raise AssertionError("Concurrent writer did not finish")
                    if progress is not None:
                        progress(status, remaining, total)

                super().backup(
                    target, pages=1, progress=observe, name=name, sleep=sleep
                )

        def connect(
            path: Path,
            deadline: backup._Deadline,
            *,
            writable: bool = False,
            immutable: bool = False,
        ) -> sqlite3.Connection:
            if path == self.source and not writable:
                return sqlite3.connect(
                    path.as_uri() + "?mode=ro", uri=True, factory=ObservedConnection
                )
            return real_connect(path, deadline, writable=writable, immutable=immutable)

        with closing(sqlite3.connect(self.source)) as writer:
            writer.execute("PRAGMA journal_mode = WAL")
            writer.execute("INSERT INTO records VALUES (2, ?)", ("x" * 100000,))
            writer.commit()
            with patch.object(backup, "_connect", side_effect=connect):
                with ThreadPoolExecutor(max_workers=1) as executor:
                    future = executor.submit(
                        self.service.create, self.source, self.bundle
                    )
                    try:
                        self.assertTrue(started.wait(2))
                        writer.execute("INSERT INTO records VALUES (3, 'later')")
                        writer.commit()
                    finally:
                        committed.set()
                    future.result(timeout=3)
            self.assertEqual([row[0] for row in self._contents(self.source)], [1, 2, 3])
            self.assertEqual(
                [row[0] for row in self._contents(self.bundle / "database.sqlite3")],
                [1, 2],
            )

    def test_closed_wal_source_database_is_unchanged(self) -> None:
        """Read a closed WAL database without writing its database contents."""
        with closing(sqlite3.connect(self.source)) as writer:
            writer.execute("PRAGMA journal_mode = WAL")
        before = self.source.read_bytes()
        self._create()
        self.assertEqual(before, self.source.read_bytes())
        self.assertEqual(
            self._contents(self.bundle / "database.sqlite3"), [(1, "original")]
        )

    def test_backup_progress_cancels_a_busy_destination(self) -> None:
        """Abort SQLite's own backup busy/retry loop at the operation deadline."""
        real_connect = backup._connect

        class BusyConnection(sqlite3.Connection):
            def backup(
                self,
                target: sqlite3.Connection,
                *,
                pages: int = -1,
                progress: Callable[[int, int, int], object] | None = None,
                name: str = "main",
                sleep: float = 0.25,
            ) -> None:
                target_path = Path(target.execute("PRAGMA database_list").fetchone()[2])
                with closing(sqlite3.connect(target_path)) as locker:
                    locker.execute("BEGIN EXCLUSIVE")
                    super().backup(
                        target, pages=pages, progress=progress, name=name, sleep=sleep
                    )

        def connect(
            path: Path,
            deadline: backup._Deadline,
            *,
            writable: bool = False,
            immutable: bool = False,
        ) -> sqlite3.Connection:
            if path == self.source and not writable:
                return sqlite3.connect(
                    path.as_uri() + "?mode=ro", uri=True, factory=BusyConnection
                )
            return real_connect(path, deadline, writable=writable, immutable=immutable)

        started = time.monotonic()
        with patch.object(backup, "_connect", side_effect=connect):
            self._assert_error(
                "backup_timeout",
                lambda: SQLiteBackupService(timeout=0.15).create(
                    self.source, self.bundle
                ),
            )
        self.assertLess(time.monotonic() - started, 1.5)
        self.assertFalse(self.bundle.exists())

    def test_integrity_has_a_sqlite_progress_deadline(self) -> None:
        """Cancel SQLite work inside integrity_check, not just between file reads."""
        self._create()
        real_connect = backup._connect

        def connect(
            path: Path,
            deadline: backup._Deadline,
            *,
            writable: bool = False,
            immutable: bool = False,
        ) -> sqlite3.Connection:
            connection = real_connect(
                path, deadline, writable=writable, immutable=immutable
            )
            if immutable:
                time.sleep(0.03)
                connection.set_progress_handler(
                    lambda: int(time.monotonic() >= deadline.end), 1
                )
            return connection

        with patch.object(backup, "_connect", side_effect=connect):
            self._assert_error(
                "backup_timeout",
                lambda: SQLiteBackupService(timeout=0.02).verify(self.bundle),
            )

    def test_symlink_source_sidecar_is_rejected(self) -> None:
        """SQLite must not follow a redirected WAL before the source is opened."""
        wal = self.source.with_name(self.source.name + "-wal")
        self._symlink(self.source, wal)
        self._assert_error("backup_unsafe_path", self._create)
        self.assertFalse(self.bundle.exists())

    def test_empty_bundle_and_missing_member_are_rejected(self) -> None:
        """Neither an incomplete bundle nor an arbitrary directory is verified."""
        self.bundle.mkdir()
        self._assert_error(
            "backup_members_invalid", lambda: self.service.verify(self.bundle)
        )
        (self.bundle / "manifest.json").write_text("{}", encoding="utf-8")
        self._assert_error(
            "backup_members_invalid", lambda: self.service.verify(self.bundle)
        )

    def test_traversal_output_path_is_rejected(self) -> None:
        """Refuse ambiguous lexical parent traversal before creating outputs."""
        self._assert_error(
            "backup_unsafe_path",
            lambda: self.service.create(self.source, self.root / "x/../bundle"),
        )
        self.assertFalse(self.bundle.exists())

    @unittest.skipUnless(os.name == "nt", "Windows device-name semantics")
    def test_windows_device_names_are_rejected_before_io(self) -> None:
        """Device names and NT path namespaces are not regular output paths."""
        for name in ("NUL", "NUL.sqlite3", "CON", "AUX", "COM1", "LPT1", "trailing."):
            with self.subTest(name=name):
                self._assert_error(
                    "backup_unsafe_path",
                    lambda: self.service.create(self.source, self.root / name),
                )

    def test_existing_bundle_is_preserved(self) -> None:
        """Refuse an existing directory, retaining all of its contents."""
        self.bundle.mkdir()
        marker = self.bundle / "keep"
        marker.write_bytes(b"foreign")
        self._assert_error("backup_output_exists", self._create)
        self.assertEqual(marker.read_bytes(), b"foreign")

    def test_existing_restore_destination_is_preserved(self) -> None:
        """Never replace an operator's existing restore target."""
        self._create()
        self.destination.write_bytes(b"keep")
        self._assert_error(
            "backup_output_exists",
            lambda: self.service.restore(self.bundle, self.destination),
        )
        self.assertEqual(self.destination.read_bytes(), b"keep")

    def test_missing_source_does_not_create_outputs(self) -> None:
        """A missing source must not be initialized as an empty database."""
        self.source.unlink()
        self._assert_error("backup_path_missing", self._create)
        self.assertFalse(self.source.exists())
        self.assertFalse(self.bundle.exists())

    def test_non_sqlite_source_is_rejected(self) -> None:
        """Reject arbitrary files without changing them or creating a bundle."""
        self.source.write_bytes(b"not a database")
        self._assert_error("backup_source_invalid", self._create)
        self.assertEqual(self.source.read_bytes(), b"not a database")
        self.assertFalse(self.bundle.exists())

    def test_manifest_schema_and_member_names_are_strict(self) -> None:
        """Refuse traversal, unknown schemas, duplicate keys and nonfinite JSON."""
        self._create()
        path = self.bundle / "manifest.json"
        original = json.loads(path.read_bytes())
        candidates: list[bytes] = []
        for member in (
            "../source.sqlite3",
            "/database.sqlite3",
            "x/database.sqlite3",
            "C:\\database.sqlite3",
            "database.sqlite3:stream",
        ):
            candidate = json.loads(json.dumps(original))
            candidate["database"]["path"] = member
            candidates.append(json.dumps(candidate).encode())
        for key, value in (
            ("schema_version", 2),
            ("schema_version", True),
            ("format", "other"),
            ("integrity_check", "failed"),
            ("unexpected", "ignored?"),
        ):
            candidate = dict(original)
            candidate[key] = value
            candidates.append(json.dumps(candidate).encode())
        for key, value in (("size", True), ("size", -1), ("sha256", "x" * 64)):
            candidate = json.loads(json.dumps(original))
            candidate["database"][key] = value
            candidates.append(json.dumps(candidate).encode())
        candidates.extend(
            (
                b'{"schema_version": 1, "schema_version": 1}',
                b'{"number": NaN}',
                b"[]",
                b"\xff",
                b"{",
            )
        )
        for raw in candidates:
            with self.subTest(raw=raw[:70]):
                path.write_bytes(raw)
                self._assert_error(
                    "backup_manifest_invalid", lambda: self.service.verify(self.bundle)
                )

    def test_oversized_manifest_is_rejected(self) -> None:
        """Bound manifest parsing independently of a potentially hostile file."""
        self._create()
        (self.bundle / "manifest.json").write_bytes(b" " * 65537)
        self._assert_error(
            "backup_manifest_invalid", lambda: self.service.verify(self.bundle)
        )

    def test_same_size_same_mtime_database_tamper_is_detected(self) -> None:
        """Metadata equality must not replace a full database checksum."""
        self._create()
        database = self.bundle / "database.sqlite3"
        before = database.stat()
        data = bytearray(database.read_bytes())
        data[-1] ^= 1
        database.write_bytes(data)
        os.utime(database, ns=(before.st_atime_ns, before.st_mtime_ns))
        self._assert_error(
            "backup_hash_mismatch", lambda: self.service.verify(self.bundle)
        )
        with self.assertRaises(MaintenanceError):
            self.service.restore(self.bundle, self.destination)
        self.assertFalse(self.destination.exists())

    def test_integrity_is_checked_even_with_matching_hash(self) -> None:
        """Recomputing a corrupt database's hash cannot bypass SQLite validation."""
        self._create()
        database = self.bundle / "database.sqlite3"
        data = bytearray(database.read_bytes())
        data[100] = 0  # Invalid first b-tree page type, retaining a SQLite header.
        database.write_bytes(data)
        manifest = self.bundle / "manifest.json"
        document = json.loads(manifest.read_bytes())
        document["database"]["sha256"] = hashlib.sha256(data).hexdigest()
        manifest.write_text(json.dumps(document), encoding="utf-8")
        with self.assertRaises(MaintenanceError):
            self.service.verify(self.bundle)

    def test_metadata_tamper_is_detected(self) -> None:
        """Validate declared SQLite facts against the actual database."""
        self._create()
        manifest = self.bundle / "manifest.json"
        document = json.loads(manifest.read_bytes())
        document["sqlite"]["user_version"] += 1
        manifest.write_text(json.dumps(document), encoding="utf-8")
        self._assert_error(
            "backup_metadata_mismatch", lambda: self.service.verify(self.bundle)
        )

    def test_unexpected_bundle_members_are_rejected(self) -> None:
        """Sidecars or undeclared members must never affect bundle interpretation."""
        self._create()
        for name in ("database.sqlite3-wal", "database.sqlite3-shm", "extra"):
            with self.subTest(member=name):
                member = self.bundle / name
                member.write_bytes(b"untrusted")
                self._assert_error(
                    "backup_members_invalid", lambda: self.service.verify(self.bundle)
                )
                member.unlink()

    def test_source_symlink_is_rejected(self) -> None:
        """Never follow a symlink to a source database."""
        link = self.root / "link.sqlite3"
        self._symlink(self.source, link)
        self._assert_error(
            "backup_unsafe_path", lambda: self.service.create(link, self.bundle)
        )
        self.assertFalse(self.bundle.exists())

    def test_bundle_member_symlink_is_rejected(self) -> None:
        """A declared file cannot redirect reads outside its bundle."""
        self._create()
        database = self.bundle / "database.sqlite3"
        database.unlink()
        self._symlink(self.source, database)
        self._assert_error(
            "backup_unsafe_path", lambda: self.service.verify(self.bundle)
        )

    def test_symlink_parent_is_rejected(self) -> None:
        """Checking only the final component is insufficient for containment."""
        alias = self.root / "alias"
        self._symlink(self.root, alias)
        self._assert_error(
            "backup_unsafe_path",
            lambda: self.service.create(self.source, alias / "bundle"),
        )
        self.assertFalse(self.bundle.exists())

    def test_dangling_restore_symlink_is_preserved(self) -> None:
        """A dangling link still occupies the requested output path."""
        self._create()
        self._symlink(self.root / "absent", self.destination)
        self._assert_error(
            "backup_unsafe_path",
            lambda: self.service.restore(self.bundle, self.destination),
        )
        self.assertTrue(self.destination.is_symlink())
        self.assertFalse((self.root / "absent").exists())

    def test_hardlinked_bundle_member_is_rejected(self) -> None:
        """Refuse aliases allowing bundle data to change via another pathname."""
        self._create()
        try:
            os.link(self.bundle / "database.sqlite3", self.root / "external-alias")
        except OSError:
            self.skipTest("Hard links are unavailable on this filesystem")
        self._assert_error(
            "backup_unsafe_path", lambda: self.service.verify(self.bundle)
        )

    def test_restore_inside_bundle_is_rejected(self) -> None:
        """Restore cannot add undeclared members to its verified input."""
        self._create()
        self._assert_error(
            "backup_unsafe_path",
            lambda: self.service.restore(self.bundle, self.bundle / "restored"),
        )
        self.assertEqual(len(list(self.bundle.iterdir())), 2)

    def test_restore_refuses_preexisting_sidecars(self) -> None:
        """A new filename must not inherit a stale WAL or rollback journal."""
        self._create()
        for suffix in ("-wal", "-shm", "-journal"):
            with self.subTest(suffix=suffix):
                member = self.destination.with_name(self.destination.name + suffix)
                member.write_bytes(b"keep")
                self._assert_error(
                    "backup_unsafe_sidecar",
                    lambda: self.service.restore(self.bundle, self.destination),
                )
                self.assertFalse(self.destination.exists())
                self.assertEqual(member.read_bytes(), b"keep")
                member.unlink()

    def test_create_io_failure_cleans_only_its_bundle(self) -> None:
        """Remove owned failed staging, preserving source and neighboring files."""
        original = self.source.read_bytes()
        foreign = self.root / "keep"
        foreign.write_bytes(b"foreign")
        with patch.object(backup, "_backup", side_effect=OSError("private diagnostic")):
            self._assert_error("backup_io_failed", self._create)
        self.assertFalse(self.bundle.exists())
        self.assertEqual(original, self.source.read_bytes())
        self.assertEqual(foreign.read_bytes(), b"foreign")

    def test_interruption_cleans_failed_create(self) -> None:
        """Cleanup also runs when an attempt is interrupted."""
        with patch.object(backup, "_backup", side_effect=KeyboardInterrupt):
            with self.assertRaises(KeyboardInterrupt):
                self._create()
        self.assertFalse(self.bundle.exists())

    def test_failure_immediately_after_allocation_cleans_staging(self) -> None:
        """Cleanup must also cover failures before a new file is yielded."""
        real_check = backup._File.check

        def check(opened: backup._File) -> os.stat_result:
            if opened.path == self.bundle / "database.sqlite3":
                raise OSError("injected allocation failure")
            return real_check(opened)

        with patch.object(backup._File, "check", new=check):
            self._assert_error("backup_io_failed", self._create)
        self.assertFalse(self.bundle.exists())

    def test_cleanup_does_not_delete_foreign_bundle_entries(self) -> None:
        """Refuse recursive cleanup when an unexpected file has appeared."""

        def fail(source: Path, target: Path, deadline: backup._Deadline) -> None:
            (self.bundle / "foreign").write_bytes(b"keep")
            raise OSError("injected failure")

        with patch.object(backup, "_backup", side_effect=fail):
            self._assert_error("backup_cleanup_failed", self._create)
        self.assertEqual((self.bundle / "foreign").read_bytes(), b"keep")
        self.assertFalse((self.bundle / "database.sqlite3").exists())

    def test_restore_io_failure_removes_only_new_destination(self) -> None:
        """A post-copy failure must retain the backup and remove the failed file."""
        self._create()
        original = {p.name: p.read_bytes() for p in self.bundle.iterdir()}
        real_integrity = backup._integrity

        def integrity(path: Path, deadline: backup._Deadline) -> dict[str, object]:
            if path == self.destination:
                raise OSError("injected validation failure")
            return real_integrity(path, deadline)

        with patch.object(backup, "_integrity", side_effect=integrity):
            self._assert_error(
                "backup_io_failed",
                lambda: self.service.restore(self.bundle, self.destination),
            )
        self.assertFalse(self.destination.exists())
        self.assertEqual(
            original, {p.name: p.read_bytes() for p in self.bundle.iterdir()}
        )

    def test_database_change_during_verify_is_detected(self) -> None:
        """Rehash after integrity_check instead of trusting a previous checksum."""
        self._create()
        real_integrity = backup._integrity

        def integrity(path: Path, deadline: backup._Deadline) -> dict[str, object]:
            result = real_integrity(path, deadline)
            data = bytearray(path.read_bytes())
            data[-1] ^= 1
            path.write_bytes(data)
            return result

        with patch.object(backup, "_integrity", side_effect=integrity):
            self._assert_error(
                "backup_changed", lambda: self.service.verify(self.bundle)
            )

    def test_bundle_change_between_verify_and_restore_is_detected(self) -> None:
        """Restore must copy the bytes it verified, even across the allocation gap."""
        self._create()
        real_open = backup._open_file

        @contextmanager
        def open_file(path: Path, *, create: bool = False) -> Iterator[backup._File]:
            with real_open(path, create=create) as opened:
                if create and path == self.destination:
                    database = self.bundle / "database.sqlite3"
                    data = bytearray(database.read_bytes())
                    data[-1] ^= 1
                    database.write_bytes(data)
                yield opened

        with patch.object(backup, "_open_file", side_effect=open_file):
            self._assert_error(
                "backup_hash_mismatch",
                lambda: self.service.restore(self.bundle, self.destination),
            )
        self.assertFalse(self.destination.exists())

    def test_manifest_change_during_restore_is_detected(self) -> None:
        """Post-copy checks must include the manifest and retain no failed restore."""
        self._create()
        real_integrity = backup._integrity

        def integrity(path: Path, deadline: backup._Deadline) -> dict[str, object]:
            result = real_integrity(path, deadline)
            if path == self.destination:
                manifest = self.bundle / "manifest.json"
                manifest.write_bytes(manifest.read_bytes() + b" ")
            return result

        with patch.object(backup, "_integrity", side_effect=integrity):
            self._assert_error(
                "backup_changed",
                lambda: self.service.restore(self.bundle, self.destination),
            )
        self.assertFalse(self.destination.exists())

    def test_exclusive_source_lock_has_a_bounded_wait(self) -> None:
        """An uncooperative source must not keep the operation waiting forever."""
        with closing(sqlite3.connect(self.source)) as writer:
            writer.execute("BEGIN EXCLUSIVE")
            started = time.monotonic()
            with self.assertRaises(MaintenanceError):
                SQLiteBackupService(timeout=0.15).create(self.source, self.bundle)
            self.assertLess(time.monotonic() - started, 1.5)
            writer.rollback()
        self.assertFalse(self.bundle.exists())

    def test_concurrent_create_has_one_winner(self) -> None:
        """The losing creator must not remove the successful creator's files."""
        with ThreadPoolExecutor(max_workers=2) as executor:
            attempts = [
                executor.submit(self.service.create, self.source, self.bundle)
                for _ in range(2)
            ]
            successes, failures = 0, []
            for attempt in attempts:
                try:
                    attempt.result(timeout=4)
                    successes += 1
                except MaintenanceError as exc:
                    failures.append(exc.code)
        self.assertEqual(successes, 1)
        self.assertEqual(failures, ["backup_output_exists"])
        self.assertEqual(self.service.verify(self.bundle)["status"], "ok")

    def test_concurrent_restore_has_one_winner(self) -> None:
        """Exclusive allocation must hold across simultaneous restore attempts."""
        self._create()
        with ThreadPoolExecutor(max_workers=2) as executor:
            attempts = [
                executor.submit(self.service.restore, self.bundle, self.destination)
                for _ in range(2)
            ]
            successes, failures = 0, []
            for attempt in attempts:
                try:
                    attempt.result(timeout=4)
                    successes += 1
                except MaintenanceError as exc:
                    failures.append(exc.code)
        self.assertEqual(successes, 1)
        self.assertEqual(failures, ["backup_output_exists"])
        self.assertEqual(self._contents(self.destination), [(1, "original")])
