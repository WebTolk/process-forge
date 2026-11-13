"""Real SQLite journal refusal and primary-error preservation on both platforms."""

from __future__ import annotations

import asyncio
import hashlib
import sqlite3
from contextlib import closing
from pathlib import Path
from typing import Any

import pytest

from processforge_core.database import SQLiteDriver
from processforge_core.process_event_journal import ProcessEventJournal
from processforge_core.raw_hook_journal import RawHookJournal
from processforge_core.sqlite_storage import JournalError, transaction


def append(
    kind: str, path: Path, identifier: str, driver: SQLiteDriver | None = None
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
            "received_at": "2026-11-13T00:00:00Z",
        },
    )
    return result["accepted"] is True


def schema_facts(path: Path) -> tuple[Any, ...]:
    with closing(
        sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True)
    ) as connection:
        return (
            connection.execute("PRAGMA application_id").fetchone()[0],
            connection.execute("PRAGMA user_version").fetchone()[0],
            connection.execute(
                "SELECT type, name, tbl_name, sql FROM sqlite_master ORDER BY type, name"
            ).fetchall(),
        )


def identifiers(kind: str, path: Path) -> set[str]:
    table, column = (
        ("admissions", "event_id") if kind == "events" else ("receipts", "raw_event_id")
    )
    with closing(
        sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True)
    ) as connection:
        return {
            str(row[0]) for row in connection.execute(f"SELECT {column} FROM {table}")
        }


@pytest.mark.parametrize("kind", ["events", "raw"])
@pytest.mark.parametrize("trigger", [False, True])
@pytest.mark.parametrize("writable", [True, False])
def test_foreign_schema_objects_are_preserved(
    tmp_path: Path, kind: str, trigger: bool, writable: bool
) -> None:
    path = tmp_path / "foreign.sqlite3"
    with closing(sqlite3.connect(path, isolation_level=None)) as seed:
        seed.execute("CREATE VIEW unrelated AS SELECT 1 AS value")
        if trigger:
            seed.execute(
                "CREATE TRIGGER foreign_insert INSTEAD OF INSERT ON unrelated BEGIN SELECT NEW.value; END"
            )
    facts = schema_facts(path)
    assert facts[:2] == (0, 0)
    before = {
        item.name: item.read_bytes() for item in tmp_path.iterdir() if item.is_file()
    }
    code = "journal_schema_unrecognized" if writable else "journal_schema_unsupported"
    with pytest.raises(JournalError, match="^" + code + "$"):
        if writable:
            append(kind, path, "must-not-write")
        else:
            journal = ProcessEventJournal if kind == "events" else RawHookJournal
            with journal.connection(path):
                pytest.fail("foreign read was accepted")
    assert schema_facts(path) == facts
    assert {
        item.name: item.read_bytes() for item in tmp_path.iterdir() if item.is_file()
    } == before


@pytest.mark.parametrize("kind", ["events", "raw"])
@pytest.mark.parametrize("initial", ["missing", "empty-file", "wal-empty"])
def test_empty_store_still_initializes(tmp_path: Path, kind: str, initial: str) -> None:
    path = tmp_path / "empty.sqlite3"
    if initial != "missing":
        with closing(sqlite3.connect(path, isolation_level=None)) as seed:
            if initial == "wal-empty":
                assert seed.execute("PRAGMA journal_mode=WAL").fetchone()[0] == "wal"
    assert append(kind, path, "accepted")
    assert append(kind, path, "accepted") is (kind == "raw")
    assert identifiers(kind, path) == {"accepted"}
    application_id, version, _schema = schema_facts(path)
    assert application_id != 0 and version == 1


class FaultConnection(sqlite3.Connection):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.failure_stage = "none"
        self.primary: BaseException = RuntimeError("unused primary")
        self.rollback_error = sqlite3.OperationalError("rollback-secret")
        self.rollback_timing: str | None = None
        self.rollback_calls = 0
        self.rollback_states: list[bool] = []
        self.native_commit_error: sqlite3.Error | None = None

    def execute(self, sql: str, parameters: Any = (), /) -> sqlite3.Cursor:
        if sql == "ROLLBACK":
            self.rollback_calls += 1
            self.rollback_states.append(self.in_transaction)
            if self.rollback_timing == "before":
                raise self.rollback_error
            result = super().execute(sql, parameters)
            self.rollback_states.append(self.in_transaction)
            if self.rollback_timing == "after":
                raise self.rollback_error
            return result
        if self.failure_stage == "commit" and sql == "COMMIT":
            raise self.primary
        if self.failure_stage in {"body", "cancelled"} and sql.startswith(
            ("INSERT INTO admissions", "INSERT INTO receipts")
        ):
            raise self.primary
        try:
            return super().execute(sql, parameters)
        except sqlite3.Error as error:
            if sql == "COMMIT":
                self.native_commit_error = error
            raise


def primary_error(stage: str) -> BaseException:
    if stage == "cancelled":
        return asyncio.CancelledError("fixture primary cancellation")
    if stage == "commit":
        return sqlite3.OperationalError("fixture primary commit")
    return ValueError("fixture primary body")


def fault_driver(
    stage: str,
    primary: BaseException,
    timing: str | None,
    opened: list[FaultConnection],
) -> SQLiteDriver:
    class Driver(SQLiteDriver):
        def _connect(self, target: str, **kwargs: Any) -> sqlite3.Connection:
            connection = sqlite3.connect(target, factory=FaultConnection, **kwargs)
            assert isinstance(connection, FaultConnection)
            connection.failure_stage = stage
            connection.primary = primary
            connection.rollback_timing = timing
            opened.append(connection)
            return connection

    return Driver()


def assert_rollback_diagnostic(primary: BaseException) -> None:
    notes = getattr(primary, "__notes__", [])
    assert any(
        "journal_rollback_failed" in note and "transaction_outcome_unknown" in note
        for note in notes
    )
    assert "rollback-secret" not in "\n".join(notes)


def journal_failure(tmp_path: Path, kind: str, stage: str, timing: str | None) -> None:
    path = tmp_path / "journal.sqlite3"
    assert append(kind, path, "accepted")
    primary = primary_error(stage)
    opened: list[FaultConnection] = []
    with pytest.raises(BaseException) as caught:
        append(kind, path, "pending", fault_driver(stage, primary, timing, opened))
    if isinstance(primary, sqlite3.Error):
        assert isinstance(caught.value, JournalError)
        assert caught.value.__cause__ is primary
    else:
        assert caught.value is primary
    assert len(opened) == 1
    assert opened[0].rollback_calls == 1
    assert opened[0].rollback_states == (
        [True] if timing == "before" else [True, False]
    )
    if timing is None:
        assert not getattr(primary, "__notes__", [])
    else:
        assert_rollback_diagnostic(primary)
    # This controlled connection closes normally; it does not prove the outcome
    # of an actual failed native rollback or a failed native close.
    assert identifiers(kind, path) == {"accepted"}


@pytest.mark.parametrize("kind", ["events", "raw"])
@pytest.mark.parametrize("stage", ["body", "commit", "cancelled"])
@pytest.mark.parametrize("timing", ["before", "after"])
def test_journal_rollback_failure_preserves_primary(
    tmp_path: Path, kind: str, stage: str, timing: str
) -> None:
    journal_failure(tmp_path, kind, stage, timing)


@pytest.mark.parametrize("kind", ["events", "raw"])
@pytest.mark.parametrize("stage", ["body", "commit", "cancelled"])
def test_successful_rollback_preserves_existing_error_contract(
    tmp_path: Path, kind: str, stage: str
) -> None:
    journal_failure(tmp_path, kind, stage, None)


def direct_connection(path: Path) -> FaultConnection:
    connection = sqlite3.connect(path, factory=FaultConnection, isolation_level=None)
    assert isinstance(connection, FaultConnection)
    connection.execute("CREATE TABLE accepted(value TEXT PRIMARY KEY)")
    connection.execute("INSERT INTO accepted VALUES ('seed')")
    return connection


@pytest.mark.parametrize("stage", ["body", "commit", "cancelled"])
@pytest.mark.parametrize("timing", ["before", "after"])
def test_transaction_rollback_failure_keeps_original_exception(
    tmp_path: Path, stage: str, timing: str
) -> None:
    with closing(direct_connection(tmp_path / "direct.sqlite3")) as connection:
        primary = primary_error(stage)
        connection.primary = primary
        connection.failure_stage = stage
        connection.rollback_timing = timing
        with pytest.raises(BaseException) as caught:
            with transaction(connection):
                connection.execute("INSERT INTO accepted VALUES ('pending')")
                if stage != "commit":
                    raise primary
        assert caught.value is primary
        assert connection.rollback_calls == 1
        assert connection.in_transaction is (timing == "before")
        assert_rollback_diagnostic(primary)


@pytest.mark.parametrize("timing", ["before", "after"])
def test_actual_asyncio_cancellation_survives_rollback_failure(
    tmp_path: Path, timing: str
) -> None:
    with closing(direct_connection(tmp_path / "cancel.sqlite3")) as connection:
        connection.rollback_timing = timing
        original: list[BaseException] = []
        outside: list[BaseException] = []

        async def scenario() -> tuple[bool, BaseException | None]:
            entered = asyncio.Event()

            async def worker() -> None:
                try:
                    with transaction(connection):
                        connection.execute("INSERT INTO accepted VALUES ('pending')")
                        entered.set()
                        try:
                            await asyncio.Future[None]()
                        except asyncio.CancelledError as error:
                            original.append(error)
                            raise
                except BaseException as error:
                    outside.append(error)
                    raise

            task = asyncio.create_task(worker())
            await entered.wait()
            task.cancel("fixture actual task cancellation")
            observed = None
            try:
                await task
            except BaseException as error:
                observed = error
            return task.cancelled(), observed

        cancelled, observed = asyncio.run(scenario())
        assert len(original) == len(outside) == 1
        assert observed is outside[0] is original[0]
        assert cancelled
        assert connection.rollback_calls == 1
        assert_rollback_diagnostic(original[0])


def test_native_deferred_constraint_commit_error_survives_rollback_failure(
    tmp_path: Path,
) -> None:
    with closing(direct_connection(tmp_path / "constraint.sqlite3")) as connection:
        connection.execute("PRAGMA foreign_keys=ON")
        connection.execute("CREATE TABLE parent(id INTEGER PRIMARY KEY)")
        connection.execute(
            "CREATE TABLE child(parent_id INTEGER REFERENCES parent(id) DEFERRABLE INITIALLY DEFERRED)"
        )
        connection.rollback_timing = "before"
        with pytest.raises(BaseException) as caught:
            with transaction(connection):
                connection.execute("INSERT INTO child VALUES (123)")
        primary = connection.native_commit_error
        assert isinstance(primary, sqlite3.IntegrityError)
        assert primary.sqlite_errorcode == sqlite3.SQLITE_CONSTRAINT_FOREIGNKEY
        assert caught.value is primary
        assert connection.rollback_calls == 1 and connection.in_transaction
        assert_rollback_diagnostic(primary)


@pytest.mark.parametrize("reject_attribute", [False, True])
def test_note_attachment_cannot_replace_the_primary(
    tmp_path: Path, reject_attribute: bool
) -> None:
    class UserError(RuntimeError):
        def add_note(self, note: str) -> None:
            raise AssertionError("user override must not be called")

        def __setattr__(self, name: str, value: Any) -> None:
            if reject_attribute and name == "__notes__":
                raise RuntimeError("fixture annotation refusal")
            super().__setattr__(name, value)

    with closing(direct_connection(tmp_path / "note.sqlite3")) as connection:
        primary = UserError("fixture original failure")
        connection.rollback_timing = "before"
        with pytest.raises(BaseException) as caught:
            with transaction(connection):
                raise primary
        assert caught.value is primary
        if not reject_attribute:
            assert_rollback_diagnostic(primary)
