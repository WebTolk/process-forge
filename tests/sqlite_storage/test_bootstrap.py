"""Real journal initialization interleaves and refusal without adoption."""

from __future__ import annotations

import hashlib
import os
import sqlite3
import sys
import tempfile
import unittest
from contextlib import closing
from pathlib import Path
from typing import Any, Literal

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


if __name__ == "__main__":
    unittest.main()
