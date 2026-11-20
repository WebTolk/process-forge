"""Real journal initialization interleaves and refusal without adoption."""

from __future__ import annotations

import hashlib
import multiprocessing
import os
import sqlite3
import sys
import tempfile
import time
import unittest
from contextlib import closing, contextmanager
from pathlib import Path
from typing import Any, Iterator, Literal, Self

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from processforge_core.database import SQLiteDriver  # noqa: E402
from processforge_core.process_event_journal import (  # noqa: E402
    APPLICATION_ID as EVENTS_ID,
)
from processforge_core.process_event_journal import ProcessEventJournal  # noqa: E402
from processforge_core.raw_hook_journal import APPLICATION_ID as RAW_ID  # noqa: E402
from processforge_core.raw_hook_journal import RawHookJournal  # noqa: E402
from processforge_core.sqlite_storage import (  # noqa: E402
    JournalError,
    JournalMigrationRequired,
    _enable_wal,
)

Kind = Literal["events", "raw"]
KINDS: tuple[Kind, ...] = ("events", "raw")


def append(
    kind: Kind, path: Path, identifier: str, driver: SQLiteDriver | None = None
) -> bool:
    if kind == "events":
        return ProcessEventJournal(driver=driver).append(path, {"event_id": identifier})
    result = RawHookJournal(driver=driver).accept(
        path,
        {
            "raw_event_id": identifier,
            "raw_payload_hash": "sha256:"
            + hashlib.sha256(identifier.encode()).hexdigest(),
            "provider": "fixture",
            "adapter": "fixture",
            "received_at": "2026-11-12T00:00:00Z",
        },
    )
    return result["accepted"] is True


def headers(path: Path) -> tuple[int, int]:
    with closing(sqlite3.connect(path, isolation_level=None)) as connection:
        return (
            int(connection.execute("PRAGMA application_id").fetchone()[0]),
            int(connection.execute("PRAGMA user_version").fetchone()[0]),
        )


def identifiers(kind: Kind, path: Path) -> set[str]:
    journal = ProcessEventJournal if kind == "events" else RawHookJournal
    table, column = (
        ("admissions", "event_id") if kind == "events" else ("receipts", "raw_event_id")
    )
    with journal.connection(path) as connection:
        return {
            str(row[0]) for row in connection.execute(f"SELECT {column} FROM {table}")
        }


def hold_rollback_writer(path: str, ready: Any, release: Any) -> None:
    """A real independent writer; the parent controls only when it commits."""
    with closing(sqlite3.connect(path, isolation_level=None)) as connection:
        connection.execute("BEGIN IMMEDIATE")
        connection.execute("INSERT INTO journal_metadata VALUES ('holder', 'kept')")
        ready.set()
        if not release.wait(30):
            raise RuntimeError("writer release was not signalled")
        connection.execute("COMMIT")


def observing_driver(
    *, release: Any = None, timeout: int = 10000, error: sqlite3.Error | None = None
) -> tuple[SQLiteDriver, dict[str, Any]]:
    observations: dict[str, Any] = {
        "attempts": [],
        "busy": [],
        "closed_timeout": [],
        "publication_timeout": [],
        "attempt_timeouts": [],
    }

    class Cursor(sqlite3.Cursor):
        was_closed = False

        def execute(self, sql: str, parameters: Any = (), /) -> Self:
            if sql in ("PRAGMA journal_mode = WAL", "BEGIN IMMEDIATE"):
                with closing(
                    sqlite3.Connection.execute(self.connection, "PRAGMA busy_timeout")
                ) as settings:
                    current_timeout = int(settings.fetchone()[0])
                key = (
                    "attempt_timeouts"
                    if sql == "PRAGMA journal_mode = WAL"
                    else "publication_timeout"
                )
                observations[key].append(current_timeout)
            if sql == "PRAGMA journal_mode = WAL":
                observations["attempts"].append(self)
                if error is not None:
                    raise error
            try:
                return super().execute(sql, parameters)
            except sqlite3.OperationalError as actual:
                if sql == "PRAGMA journal_mode = WAL":
                    code = actual.sqlite_errorcode
                    observations["busy"].append(code)
                    if release is not None and code & 255 == sqlite3.SQLITE_BUSY:
                        release.set()
                raise

        def close(self) -> None:
            super().close()
            self.was_closed = True

    class Connection(sqlite3.Connection):
        def cursor(self, factory: Any = None) -> Any:
            return super().cursor(Cursor if factory is None else factory)

        def execute(self, sql: str, parameters: Any = (), /) -> sqlite3.Cursor:
            if sql == "PRAGMA busy_timeout = 10000":
                sql = f"PRAGMA busy_timeout = {timeout}"
            return self.cursor().execute(sql, parameters)

        def close(self) -> None:
            with closing(super().execute("PRAGMA busy_timeout")) as cursor:
                observations["closed_timeout"].append(int(cursor.fetchone()[0]))
            super().close()

    class Driver(SQLiteDriver):
        def _connect(self, database: str | Path, **kwargs: Any) -> sqlite3.Connection:
            return sqlite3.connect(database, factory=Connection, **kwargs)

    return Driver(), observations


class BootstrapTests(unittest.TestCase):
    def setUp(self) -> None:
        configured = os.environ.get("PF_TEST_SCRATCH_ROOT")
        scratch = Path(configured).resolve() if configured else None
        if scratch is not None:
            scratch.mkdir(parents=True, exist_ok=True)
        directory = tempfile.TemporaryDirectory(
            prefix="pf-journal-bootstrap-", dir=scratch
        )
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name).resolve()

    def test_other_initializer_commits_between_header_reads(self) -> None:
        for kind in KINDS:
            with self.subTest(kind=kind):
                path = self.root / (kind + ".sqlite3")
                expected_id = EVENTS_ID if kind == "events" else RAW_ID
                with closing(sqlite3.connect(path, isolation_level=None)) as setup:
                    self.assertEqual(
                        setup.execute("PRAGMA journal_mode=WAL").fetchone()[0],
                        "wal",
                    )
                seen: list[int] = []
                case = self

                class HeaderCursor(sqlite3.Cursor):
                    def fetchone(self) -> Any:
                        row = super().fetchone()
                        self.close()  # End the first real autocommit statement.
                        seen.append(int(row[0]))
                        case.assertEqual(seen, [0])
                        case.assertTrue(append(kind, path, "other-writer"))
                        case.assertEqual(headers(path), (expected_id, 1))
                        return row

                class Reader(sqlite3.Connection):
                    def execute(
                        self, sql: str, parameters: Any = (), /
                    ) -> sqlite3.Cursor:
                        if sql == "PRAGMA application_id" and not seen:
                            return self.cursor(factory=HeaderCursor).execute(
                                sql, parameters
                            )
                        return super().execute(sql, parameters)

                class InterleavingDriver(SQLiteDriver):
                    def _connect(
                        self, target: str, **kwargs: Any
                    ) -> sqlite3.Connection:
                        return sqlite3.connect(target, factory=Reader, **kwargs)

                self.assertTrue(
                    append(kind, path, "observing-writer", InterleavingDriver())
                )
                self.assertEqual(seen, [0])  # The real interleave actually ran.
                self.assertEqual(
                    identifiers(kind, path), {"other-writer", "observing-writer"}
                )
                append(kind, path, "observing-writer")
                self.assertEqual(
                    identifiers(kind, path), {"other-writer", "observing-writer"}
                )
                self.assertEqual(headers(path), (expected_id, 1))

    def test_partial_or_foreign_headers_preserve_existing_data(self) -> None:
        for kind in KINDS:
            expected = EVENTS_ID if kind == "events" else RAW_ID
            for application_id, version in (
                (0, 1),
                (expected, 0),
                (expected ^ 0x11, 0),
                (expected ^ 0x11, 1),
                (expected, 2),
            ):
                with self.subTest(kind=kind, header=(application_id, version)):
                    path = self.root / f"{kind}-{application_id}-{version}.sqlite3"
                    with closing(sqlite3.connect(path, isolation_level=None)) as seed:
                        seed.execute("CREATE TABLE foreign_data(value TEXT)")
                        seed.execute("INSERT INTO foreign_data VALUES ('preserve')")
                        seed.execute(f"PRAGMA application_id={application_id}")
                        seed.execute(f"PRAGMA user_version={version}")
                    before = path.read_bytes()
                    with self.assertRaisesRegex(
                        JournalError, "^journal_schema_unsupported$"
                    ):
                        append(kind, path, "must-not-write")
                    self.assertEqual(path.read_bytes(), before)
                    self.assertEqual(headers(path), (application_id, version))

    def test_unrecognized_tables_are_not_initialized(self) -> None:
        for kind in KINDS:
            with self.subTest(kind=kind):
                path = self.root / (kind + "-unknown.sqlite3")
                with closing(sqlite3.connect(path, isolation_level=None)) as seed:
                    seed.execute("CREATE TABLE foreign_data(value TEXT)")
                    seed.execute("INSERT INTO foreign_data VALUES ('preserve')")
                before = path.read_bytes()
                with self.assertRaisesRegex(
                    JournalError, "^journal_schema_unrecognized$"
                ):
                    append(kind, path, "must-not-write")
                self.assertEqual(path.read_bytes(), before)
                self.assertEqual(headers(path), (0, 0))

    def test_read_only_does_not_create_or_initialize(self) -> None:
        for kind in KINDS:
            with self.subTest(kind=kind):
                journal = ProcessEventJournal if kind == "events" else RawHookJournal
                path = self.root / (kind + "-read.sqlite3")
                with self.assertRaises(FileNotFoundError), journal.connection(path):
                    self.fail("missing store was accepted")
                self.assertFalse(path.exists())
                with closing(sqlite3.connect(path)):
                    pass
                before = path.read_bytes()
                with (
                    self.assertRaisesRegex(
                        JournalError, "^journal_schema_unsupported$"
                    ),
                    journal.connection(path),
                ):
                    self.fail("uninitialized store was accepted")
                self.assertEqual(path.read_bytes(), before)
                self.assertEqual(headers(path), (0, 0))

    def test_migration_barrier_preserves_accepted_record(self) -> None:
        for kind in KINDS:
            with self.subTest(kind=kind):
                path = self.root / (kind + "-pending.sqlite3")
                self.assertTrue(append(kind, path, "accepted"))
                with closing(sqlite3.connect(path, isolation_level=None)) as seed:
                    seed.execute(
                        "UPDATE journal_metadata SET value='importing' "
                        "WHERE key='migration_state'"
                    )
                before = path.read_bytes()
                with self.assertRaisesRegex(
                    JournalMigrationRequired, "^journal_migration_incomplete$"
                ):
                    append(kind, path, "must-not-write")
                self.assertEqual(path.read_bytes(), before)


class WalActivationTests(unittest.TestCase):
    root: Path
    setUp = BootstrapTests.setUp

    @contextmanager
    def held_journal(self, kind: Kind, suffix: str) -> Iterator[tuple[Path, Any]]:
        path = self.root / (kind + suffix + ".sqlite3")
        self.assertTrue(append(kind, path, "seed"))
        with closing(sqlite3.connect(path, isolation_level=None)) as connection:
            self.assertEqual(
                connection.execute("PRAGMA journal_mode=DELETE").fetchone()[0],
                "delete",
            )
        context = multiprocessing.get_context("spawn")
        ready, release = context.Event(), context.Event()
        process = context.Process(
            target=hold_rollback_writer, args=(str(path), ready, release)
        )
        process.start()
        try:
            self.assertTrue(ready.wait(15), "independent writer did not acquire lock")
            yield path, release
        finally:
            release.set()
            process.join(15)
            if process.is_alive():
                process.terminate()
                process.join(5)
            self.assertEqual(process.exitcode, 0, "independent writer failed")

    def test_real_busy_activation_then_one_publication(self) -> None:
        for kind in KINDS:
            with (
                self.subTest(kind=kind),
                self.held_journal(kind, "-release") as (
                    path,
                    release,
                ),
            ):
                driver, observed = observing_driver(release=release)
                self.assertTrue(append(kind, path, "contender", driver))
                self.assertGreaterEqual(len(observed["attempts"]), 2)
                self.assertTrue(observed["busy"])
                self.assertTrue(
                    all(code & 255 == sqlite3.SQLITE_BUSY for code in observed["busy"])
                )
                self.assertTrue(all(c.was_closed for c in observed["attempts"]))
                self.assertEqual(observed["closed_timeout"], [10000])
                self.assertEqual(identifiers(kind, path), {"seed", "contender"})
                append(kind, path, "contender")
                self.assertEqual(observed["publication_timeout"], [10000])
                journal = ProcessEventJournal if kind == "events" else RawHookJournal
                with journal.connection(path, writable=True) as connection:
                    table = "admissions" if kind == "events" else "receipts"
                    self.assertEqual(
                        connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[
                            0
                        ],
                        2,
                    )
                    self.assertEqual(
                        connection.execute("PRAGMA journal_mode").fetchone()[0], "wal"
                    )
                    self.assertEqual(
                        connection.execute("PRAGMA synchronous").fetchone()[0], 2
                    )
                    self.assertEqual(
                        connection.execute("PRAGMA integrity_check").fetchone()[0], "ok"
                    )
                    self.assertEqual(
                        connection.execute(
                            "SELECT value FROM journal_metadata WHERE key='holder'"
                        ).fetchone()[0],
                        "kept",
                    )

    def test_real_busy_deadline_refuses_without_publication(self) -> None:
        for kind in KINDS:
            for timeout in (0, 60):
                with (
                    self.subTest(kind=kind, timeout=timeout),
                    self.held_journal(kind, f"-timeout-{timeout}") as (path, _release),
                ):
                    driver, observed = observing_driver(timeout=timeout)
                    started = time.monotonic()
                    with self.assertRaisesRegex(JournalError, "journal_database_error"):
                        append(kind, path, "refused", driver)
                    elapsed = time.monotonic() - started
                    self.assertLess(elapsed, 3)
                    self.assertGreaterEqual(elapsed, timeout / 1000 * 0.8)
                    self.assertTrue(observed["busy"])
                    self.assertTrue(all(c.was_closed for c in observed["attempts"]))
                    self.assertEqual(observed["closed_timeout"], [timeout])
                    self.assertTrue(
                        all(0 <= ms <= timeout for ms in observed["attempt_timeouts"])
                    )
                    self.assertFalse(observed["publication_timeout"])
                    self.assertEqual(identifiers(kind, path), {"seed"})

    def test_nonbusy_and_unknown_errors_are_not_retried(self) -> None:
        # Error injection checks classification, not OS concurrency qualification.
        errors = [sqlite3.OperationalError("no native code")]
        with closing(sqlite3.connect(":memory:")) as connection:
            try:
                connection.execute("SELECT * FROM missing_table")
            except sqlite3.OperationalError as actual:
                errors.append(actual)
        locked = sqlite3.OperationalError("locked")
        locked.sqlite_errorcode = sqlite3.SQLITE_LOCKED
        errors.append(locked)
        for kind in KINDS:
            for index, error in enumerate(errors):
                with (
                    self.subTest(kind=kind, error=index),
                    self.held_journal(kind, f"-error-{index}") as (path, _release),
                ):
                    driver, observed = observing_driver(error=error)
                    with self.assertRaises(JournalError) as caught:
                        append(kind, path, "refused", driver)
                    self.assertIs(caught.exception.__cause__, error)
                    self.assertEqual(len(observed["attempts"]), 1)
                    self.assertTrue(observed["attempts"][0].was_closed)
                    self.assertEqual(observed["closed_timeout"], [10000])
                    self.assertEqual(identifiers(kind, path), {"seed"})

    def test_non_wal_returned_mode_is_refused(self) -> None:
        with closing(sqlite3.connect(":memory:")) as connection:
            with self.assertRaisesRegex(JournalError, "^journal_wal_unavailable$"):
                _enable_wal(connection)
            self.assertEqual(
                connection.execute("PRAGMA busy_timeout").fetchone()[0], 5000
            )


if __name__ == "__main__":
    unittest.main()
