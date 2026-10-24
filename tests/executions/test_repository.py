"""Real-SQL repository invariants, bounded queries, migration replay and CAS."""

from __future__ import annotations

import json
import os
import time
import tracemalloc
from collections.abc import Iterator, Sequence
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from dataclasses import dataclass, replace
from pathlib import Path
from threading import Barrier
from typing import Literal
from unittest.mock import patch
from uuid import uuid4

import pytest

from processforge_core.database import (
    Database,
    DatabaseIdentity,
    DatabaseTarget,
    SchemaDefinition,
    SchemaManager,
    SQLiteDriver,
    SqlRow,
    SqlSession,
    SqlStatement,
    SqlValue,
    WriteResult,
)
from processforge_core.executions.model import (
    ExecutionError,
    ExecutionKey,
    ExecutionObservation,
    ExecutionRecord,
    ProcessIdentity,
)
from processforge_core.executions.ports import ExecutionRepository
from processforge_core.executions.projection import canonical_json
from processforge_core.executions.schema import EXECUTION_SCHEMA
from processforge_core.executions.sqlite_repository import (
    CURRENT_SQL,
    SQLiteExecutionRepository,
)

PROCESS = ProcessIdentity("test-host", "test-boot", 123, "birth-one", "owned-tree")
TOKEN = "a" * 32
STAMP = "2026-10-24T16:00:00+00:00"


def _required_row(session: SqlSession, statement: SqlStatement) -> SqlRow:
    row = session.fetch_one(statement)
    assert row is not None
    return row


def payload(task_id: str = "task", attempt: int = 1) -> str:
    """Construct an existing, complete schema-1 compatibility DTO."""
    return canonical_json(
        {
            "schema_version": 1,
            "run_id": "run",
            "task_id": task_id,
            "driver_id": "generic-shell",
            "agent_model": "",
            "status": "ready",
            "pid": None,
            "started_at": None,
            "finished_at": None,
            "exit_code": None,
            "timeout_seconds": 0,
            "attempt": attempt,
            "max_retries": 0,
            "capsule_path": "capsule.yaml",
            "worker_prompt_path": "prompt.md",
            "expected_report_path": "report.md",
            "stdout_path": "stdout.log",
            "stderr_path": "stderr.log",
            "heartbeat_path": "heartbeat.json",
            "last_heartbeat_at": None,
            "failure_reason": None,
            "old_extension": {"opaque": "unchanged"},
        }
    )


def receipt(
    record: ExecutionRecord,
    kind: Literal["process", "heartbeat", "exit", "absence", "spawn_failed"],
    sequence: int = 0,
    *,
    checksum: str = "sha256:" + "b" * 64,
    process: ProcessIdentity | None = PROCESS,
    exit_code: int | None = None,
    tree_absent: bool = False,
    observed_at: str = STAMP,
    status: str | None = None,
) -> ExecutionObservation:
    assert record.launch_token is not None
    return ExecutionObservation(
        record.key,
        record.launch_token,
        kind,
        sequence,
        checksum,
        process,
        observed_at,
        status,
        exit_code,
        tree_absent,
    )


class TracedSession:
    """Instrument actual SQL and detached rows without replacing SQLite behavior."""

    def __init__(
        self, session: SqlSession, trace: list[str], visits: list[SqlRow]
    ) -> None:
        self.session, self.trace, self.visits = session, trace, visits

    def fetch_one(self, statement: SqlStatement) -> SqlRow | None:
        self.trace.append(statement.text)
        row = self.session.fetch_one(statement)
        if row is not None:
            self.visits.append(row)
        return row

    @contextmanager
    def stream(
        self, statement: SqlStatement, *, batch_size: int = 256
    ) -> Iterator[Iterator[SqlRow]]:
        self.trace.append(statement.text)
        with self.session.stream(statement, batch_size=batch_size) as rows:

            def observed() -> Iterator[SqlRow]:
                for row in rows:
                    self.visits.append(row)
                    yield row

            yield observed()

    def execute(self, statement: SqlStatement) -> WriteResult:
        self.trace.append(statement.text)
        return self.session.execute(statement)

    def execute_many(
        self, statement: SqlStatement, rows: Sequence[tuple[SqlValue, ...]]
    ) -> WriteResult:
        self.trace.append(statement.text)
        return self.session.execute_many(statement, rows)


class TracedDriver(SQLiteDriver):
    """Retain genuine public driver transactions while recording repository I/O."""

    def __init__(self) -> None:
        self.trace: list[str] = []
        self.visits: list[SqlRow] = []

    @contextmanager
    def open(
        self,
        target: DatabaseTarget,
        *,
        mode: Literal["ro", "rw", "create"],
        timeout_ms: int,
        deadline: float | None = None,
    ) -> Iterator[SqlSession]:
        with super().open(
            target, mode=mode, timeout_ms=timeout_ms, deadline=deadline
        ) as session:
            yield TracedSession(session, self.trace, self.visits)


@dataclass
class Harness:
    database: Database
    repo: SQLiteExecutionRepository
    driver: TracedDriver
    root: Path

    def prepare(self, task_id: str = "task", attempt: int = 1) -> ExecutionRecord:
        return self.repo.allocate_attempt(
            "run", task_id, payload(task_id, attempt), generation=1
        )

    def start(self, task_id: str = "task", *, token: str = TOKEN) -> ExecutionRecord:
        record = self.prepare(task_id)
        return self.repo.reserve_start(
            record.key, expected_revision=1, generation=1, launch_token=token
        )

    def finish(self, record: ExecutionRecord) -> ExecutionRecord:
        return self.repo.apply_observation(
            receipt(record, "exit", exit_code=0, tree_absent=True),
            expected_revision=record.revision,
            generation=1,
        )


@pytest.fixture
def isolated_path(request: pytest.FixtureRequest) -> Path:
    """Use an ordinary inherited directory, without private-directory ACL changes."""
    root = Path(os.environ["W3_FIXTURE_ROOT"]) / uuid4().hex
    root.mkdir(parents=True)
    return root


def make_harness(root: Path, *, importing: bool = False) -> Harness:
    driver = TracedDriver()
    database = Database(
        driver,
        DatabaseTarget(
            root / "test.sqlite3", DatabaseIdentity(uuid4().hex, "project", "project")
        ),
    )
    SchemaManager().initialize(database, (EXECUTION_SCHEMA,))
    with database.transaction() as session:
        session.execute(
            SqlStatement(
                "INSERT INTO execution_state(singleton,project_id,generation,authority,readiness,active_coverage,revision,next_history_seq) VALUES(1,?,?,?,?,?,0,1)",
                (
                    "project",
                    0 if importing else 1,
                    "legacy" if importing else "sql",
                    "importing" if importing else "ready",
                    "complete",
                ),
            )
        )
    return Harness(
        database, SQLiteExecutionRepository(database, "project"), driver, root
    )


@pytest.fixture
def harness(isolated_path: Path) -> Harness:
    return make_harness(isolated_path)


def test_schema_is_exact_and_cold() -> None:
    assert EXECUTION_SCHEMA.namespace == "execution"
    assert EXECUTION_SCHEMA.version == 1
    assert len(EXECUTION_SCHEMA.statements) == 8


def test_directory_only_floor_replay_has_no_execution_and_allocates_eight(
    isolated_path: Path,
) -> None:
    h = make_harness(isolated_path, importing=True)
    for _ in range(2):
        with h.database.transaction() as session:
            assert h.repo.import_legacy(
                session, (), source_facts=(), next_attempt_floors=(("run", "task", 8),)
            ) == (0, 0)
            for table in (
                "execution_attempts",
                "execution_heads",
                "execution_current",
                "execution_receipt_admissions",
            ):
                assert (
                    session.fetch_one(SqlStatement(f"SELECT 1 FROM {table} LIMIT 1"))
                    is None
                )
            assert (
                _required_row(
                    session,
                    SqlStatement(
                        "SELECT next_history_seq FROM execution_state WHERE singleton=1"
                    ),
                )[0]
                == 1
            )
    with h.database.transaction() as session:
        session.execute(
            SqlStatement(
                "UPDATE execution_state SET generation=1,authority='sql',readiness='ready' WHERE singleton=1"
            )
        )
    assert h.repo.current().complete and h.repo.current().records == ()
    assert h.repo.page_history().records == ()
    assert h.repo.load_latest("run", "task") is None
    assert h.prepare().key.attempt == 8
    assert h.prepare().key.attempt == 9
    with h.database.read() as session:
        assert (
            session.fetch_one(SqlStatement("SELECT 1 FROM execution_allocation_floors"))
            is None
        )


def test_floor_checkpoint_rollback_and_resume_are_one_transaction(
    isolated_path: Path,
) -> None:
    h = make_harness(isolated_path, importing=True)
    with pytest.raises(RuntimeError, match="crash"):
        with h.database.transaction() as session:
            h.repo.import_legacy(
                session, (), source_facts=(), next_attempt_floors=(("run", "task", 8),)
            )
            session.execute(
                SqlStatement(
                    "UPDATE execution_state SET plan_checksum='checkpoint' WHERE singleton=1"
                )
            )
            raise RuntimeError("crash")
    with h.database.read() as session:
        assert (
            session.fetch_one(SqlStatement("SELECT 1 FROM execution_allocation_floors"))
            is None
        )
        assert (
            _required_row(
                session,
                SqlStatement(
                    "SELECT plan_checksum FROM execution_state WHERE singleton=1"
                ),
            )[0]
            is None
        )
    with h.database.transaction() as session:
        assert h.repo.import_legacy(
            session, (), source_facts=(), next_attempt_floors=(("run", "task", 8),)
        ) == (0, 0)
        session.execute(
            SqlStatement(
                "UPDATE execution_state SET plan_checksum='checkpoint' WHERE singleton=1"
            )
        )
    with h.database.read() as session:
        assert (
            _required_row(
                session,
                SqlStatement("SELECT next_attempt FROM execution_allocation_floors"),
            )[0]
            == 8
        )
        assert (
            _required_row(
                session,
                SqlStatement(
                    "SELECT plan_checksum FROM execution_state WHERE singleton=1"
                ),
            )[0]
            == "checkpoint"
        )


def test_floor_only_import_bounds_and_owner_are_checked(isolated_path: Path) -> None:
    h = make_harness(isolated_path, importing=True)
    floors = tuple(("run", f"task{n}", n + 1) for n in range(256))
    with h.database.transaction() as session:
        assert h.repo.import_legacy(
            session, (), source_facts=(), next_attempt_floors=floors
        ) == (0, 0)
    with pytest.raises(ValueError, match="batch"):
        with h.database.transaction() as session:
            h.repo.import_legacy(
                session,
                (),
                source_facts=(),
                next_attempt_floors=(*floors, ("run", "extra", 8)),
            )
    with pytest.raises(ExecutionError, match="identity"):
        with h.database.transaction() as session:
            session.execute(
                SqlStatement(
                    "UPDATE execution_state SET project_id='foreign' WHERE singleton=1"
                )
            )
            h.repo.import_legacy(
                session, (), source_facts=(), next_attempt_floors=(("run", "task", 8),)
            )
    with h.database.read() as session:
        assert (
            session.fetch_one(SqlStatement("SELECT 1 FROM execution_attempts")) is None
        )


def test_import_snapshot_absorbs_previously_saved_floor(isolated_path: Path) -> None:
    h = make_harness(isolated_path, importing=True)
    with h.database.transaction() as session:
        h.repo.import_legacy(
            session, (), source_facts=(), next_attempt_floors=(("run", "task", 8),)
        )
    record = ExecutionRecord(
        ExecutionKey("project", "run", "task", 3),
        None,
        1,
        1,
        "prepared",
        None,
        "pending",
        None,
        None,
        payload(attempt=3),
        0,
    )
    with h.database.transaction() as session:
        assert h.repo.import_legacy(
            session,
            (record,),
            source_facts=(
                ("legacy/status.json", "sha256:" + "a" * 64, "sha256:" + "b" * 64),
            ),
            next_attempt_floors=(),
        ) == (1, 0)
        assert (
            _required_row(
                session, SqlStatement("SELECT next_attempt FROM execution_heads")
            )[0]
            == 8
        )
        assert (
            session.fetch_one(SqlStatement("SELECT 1 FROM execution_allocation_floors"))
            is None
        )


def test_construction_is_cold_and_matches_domain_port(isolated_path: Path) -> None:
    with patch("sqlite3.connect", side_effect=AssertionError("unexpected connection")):
        database = Database(
            SQLiteDriver(),
            DatabaseTarget(
                isolated_path / "never-created.sqlite3",
                DatabaseIdentity(uuid4().hex, "project", "project"),
            ),
        )
        repository: ExecutionRepository = SQLiteExecutionRepository(database, "project")
        assert repository is not None
    assert not database.target.path.exists()


def test_heads_reservation_cas_and_stop_do_not_imply_absence(harness: Harness) -> None:
    repo = harness.repo
    first = harness.prepare()
    assert repo.current().complete and repo.current().records == ()
    starting = repo.reserve_start(
        first.key, expected_revision=1, generation=1, launch_token=TOKEN
    )
    assert starting.phase == "starting" and repo.current().records == (starting,)
    with pytest.raises(ExecutionError, match="execution_activity_unknown"):
        harness.prepare(attempt=2)
    with pytest.raises(ExecutionError, match="stale_revision"):
        repo.request_stop(
            first.key, launch_token=TOKEN, expected_revision=1, generation=1
        )
    with pytest.raises(ExecutionError, match="stale_generation"):
        repo.request_stop(
            first.key, launch_token=TOKEN, expected_revision=2, generation=0
        )
    stopping = repo.request_stop(
        first.key, launch_token=TOKEN, expected_revision=2, generation=1
    )
    assert stopping.phase == "stopping" and len(repo.current().records) == 1
    finished = harness.finish(stopping)
    assert finished.phase == "absent" and finished.outcome == "cancelled"
    assert finished.history_seq == 1 and repo.current().records == ()
    next_record = harness.prepare(attempt=2)
    assert next_record.key.attempt == 2 and repo.load(first.key) == finished
    with pytest.raises(ExecutionError, match="execution_activity_unknown"):
        repo.reserve_start(
            first.key,
            expected_revision=finished.revision,
            generation=1,
            launch_token="c" * 32,
        )


def test_receipt_idempotency_conflict_and_exact_identity(harness: Harness) -> None:
    record = harness.start()
    observation = receipt(record, "process", 5)
    running = harness.repo.apply_observation(
        observation, expected_revision=2, generation=1
    )
    assert running.process == PROCESS
    assert (
        harness.repo.apply_observation(observation, expected_revision=2, generation=1)
        == running
    )
    assert (
        harness.repo.apply_observation(
            replace(observation, sequence=4), expected_revision=1, generation=1
        )
        == running
    )
    with pytest.raises(ExecutionError, match="receipt_conflict"):
        harness.repo.apply_observation(
            replace(observation, checksum="sha256:" + "c" * 64),
            expected_revision=3,
            generation=1,
        )
    with pytest.raises(ExecutionError, match="execution_identity_conflict"):
        harness.repo.apply_observation(
            replace(
                observation, sequence=6, process=replace(PROCESS, birth_id="reused-pid")
            ),
            expected_revision=3,
            generation=1,
        )
    with pytest.raises(ExecutionError, match="execution_identity_conflict"):
        harness.repo.apply_observation(
            replace(observation, launch_token="c" * 32),
            expected_revision=3,
            generation=1,
        )
    assert harness.repo.load(record.key) == running


def test_history_highwater_collection_and_old_attempt(harness: Harness) -> None:
    first = harness.finish(harness.start())
    second = harness.finish(harness.start("task-two", token="c" * 32))
    page = harness.repo.page_history(limit=1)
    assert page.records == (first,) and page.after == 1 and page.high_water == 2
    harness.finish(harness.start("task-three", token="d" * 32))
    tail = harness.repo.page_history(after=1, high_water=page.high_water, limit=1)
    assert tail.records == (second,) and tail.after is None
    harness.prepare(attempt=2)
    updated = harness.repo.record_collection(
        first.key,
        "failed",
        first.payload_json,
        expected_revision=first.revision,
        generation=1,
    )
    assert updated.history_seq == 1 and updated.phase == "absent"
    latest = harness.repo.load_latest("run", "task")
    assert latest is not None and latest.key.attempt == 2
    assert not harness.repo.ack_projection(
        first.key, revision=updated.revision, generation=1
    )
    assert len(harness.repo.page_history().records) == 3


def test_concurrent_allocate_has_unique_monotonic_heads(harness: Harness) -> None:
    gate = Barrier(2)

    # Both submit the same complete DTO; allocation owns the numeric attempt.
    def allocate() -> int:
        gate.wait(timeout=5)
        return harness.prepare().key.attempt

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: allocate(), range(2)))
    assert sorted(results) == [1, 2]
    latest = harness.repo.load_latest("run", "task")
    assert latest is not None and latest.key.attempt == 2
    assert harness.prepare().key.attempt == 3


def historical(task: str, *, attempt: int = 1) -> ExecutionRecord:
    return ExecutionRecord(
        ExecutionKey("project", "run", task, attempt),
        None,
        1,
        1,
        "absent",
        "completed",
        "pending",
        None,
        1,
        payload(task, attempt).replace('"status":"ready"', '"status":"completed"'),
        0,
    )


def import_batch(
    harness: Harness, records: tuple[ExecutionRecord, ...]
) -> tuple[int, int]:
    facts = tuple(
        (
            f".pf/runtime/{record.key.task_id}/status.json",
            "sha256:" + "b" * 64,
            "sha256:" + "c" * 64,
        )
        for record in records
    )
    with harness.database.transaction() as session:
        return harness.repo.import_legacy(
            session,
            records,
            source_facts=facts,
            next_attempt_floors=tuple(
                (r.key.run_id, r.key.task_id, r.key.attempt + 3) for r in records
            ),
        )


def cutover(harness: Harness) -> None:
    with harness.database.transaction() as session:
        session.execute(
            SqlStatement(
                "UPDATE execution_state SET authority='sql',readiness='ready',generation=1 WHERE singleton=1"
            )
        )


def test_import_replay_floor_conflict_and_caller_rollback(isolated_path: Path) -> None:
    h = make_harness(isolated_path, importing=True)
    record = historical("task", attempt=7)
    assert not h.repo.readiness().ready
    assert import_batch(h, (record,)) == (1, 0)
    assert import_batch(h, (record,)) == (0, 1)
    with pytest.raises(ExecutionError, match="execution_identity_conflict"):
        import_batch(h, (replace(record, outcome="failed"),))
    with pytest.raises(RuntimeError, match="checkpoint failure"):
        with h.database.transaction() as session:
            other = historical("other")
            h.repo.import_legacy(
                session,
                (other,),
                source_facts=(
                    ("other.json", "sha256:" + "d" * 64, "sha256:" + "e" * 64),
                ),
                next_attempt_floors=(),
            )
            raise RuntimeError("checkpoint failure")
    cutover(h)
    assert h.repo.load(ExecutionKey("project", "run", "other", 1)) is None
    assert h.repo.page_history().high_water == 1
    assert h.prepare(attempt=10).key.attempt == 10
    with pytest.raises(ExecutionError, match="execution_storage_not_ready"):
        import_batch(h, (record,))


@pytest.mark.parametrize("history_count", [0, 510])
@pytest.mark.parametrize("current_count", [0, 1, 3])
def test_current_only_sql_plan_and_row_bounds(
    isolated_path: Path, history_count: int, current_count: int
) -> None:
    h = make_harness(isolated_path, importing=True)
    for start in range(0, history_count, 256):
        records = tuple(
            historical(f"terminal-{i}")
            for i in range(start, min(start + 256, history_count))
        )
        assert import_batch(h, records) == (len(records), 0)
    cutover(h)
    for number in range(current_count):
        h.start(f"active-{number}", token=f"{number + 1:032x}")
    h.driver.trace.clear()
    h.driver.visits.clear()
    tracemalloc.start()
    started = time.perf_counter()
    with (
        patch.object(
            Path, "glob", side_effect=AssertionError("status glob forbidden")
        ) as glob,
        patch.object(
            Path, "open", side_effect=AssertionError("terminal file read forbidden")
        ) as path_open,
        patch(
            "builtins.open", side_effect=AssertionError("terminal file read forbidden")
        ) as builtin_open,
    ):
        snapshot = h.repo.current()
    glob.assert_not_called()
    path_open.assert_not_called()
    builtin_open.assert_not_called()
    elapsed = time.perf_counter() - started
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    assert snapshot.complete and len(snapshot.records) == current_count
    assert len(h.driver.trace) == 3
    assert len(h.driver.visits) == current_count + 2
    assert not any("terminal-" in str(row.values) for row in h.driver.visits)
    assert not any(
        "COUNT(" in sql.upper() or "execution_history" in sql for sql in h.driver.trace
    )
    assert h.driver.trace[-1] == CURRENT_SQL
    with h.database.read() as session:
        with session.stream(
            SqlStatement("EXPLAIN QUERY PLAN " + CURRENT_SQL, ("project", 129))
        ) as rows:
            details = "\n".join(str(row["detail"]) for row in rows)
    assert "SEARCH c USING COVERING INDEX" in details
    assert "SEARCH a USING INDEX sqlite_autoindex_execution_attempts_" in details
    assert "(project_id=? AND run_id=? AND task_id=? AND attempt=?)" in details
    assert "SCAN a" not in details and "TEMP B-TREE" not in details
    print(
        json.dumps(
            {
                "history": history_count,
                "current": current_count,
                "sql_operations": 3,
                "returned_attempt_rows": current_count,
                "terminal_rows_returned": 0,
                "elapsed_seconds": elapsed,
                "peak_bytes": peak,
                "query_plan": details,
            }
        )
    )
    if current_count > 1:
        assert not h.repo.current(limit=1).complete


def test_unknown_missing_deadline_and_limits(
    harness: Harness, isolated_path: Path
) -> None:
    import time

    assert not harness.repo.current(deadline=time.monotonic() - 1).complete
    with harness.database.transaction() as session:
        session.execute(
            SqlStatement(
                "UPDATE execution_state SET active_coverage='unknown' WHERE singleton=1"
            )
        )
    assert not harness.repo.current().complete
    with pytest.raises(ExecutionError, match="execution_activity_unknown"):
        harness.prepare()
    for value in (0, True, 1001):
        with pytest.raises(ValueError):
            harness.repo.current(limit=value)
    missing = Database(
        SQLiteDriver(),
        DatabaseTarget(
            isolated_path / "missing.sqlite3",
            DatabaseIdentity(uuid4().hex, "project", "project"),
        ),
    )
    snapshot = SQLiteExecutionRepository(missing, "project").current()
    assert not snapshot.complete and snapshot.readiness.reason == "database_missing"
    assert not missing.target.path.exists()


def test_schema_identity_and_import_provenance_refuse(harness: Harness) -> None:
    with pytest.raises(ExecutionError, match="execution_identity_conflict"):
        harness.repo.load(ExecutionKey("another-project", "run", "task", 1))
    import hashlib

    future = SchemaDefinition(
        "execution",
        2,
        EXECUTION_SCHEMA.statements,
        "sha256:"
        + hashlib.sha256(
            canonical_json(
                {
                    "namespace": "execution",
                    "version": 2,
                    "statements": EXECUTION_SCHEMA.statements,
                }
            ).encode()
        ).hexdigest(),
    )
    database = Database(
        SQLiteDriver(),
        DatabaseTarget(
            harness.root / "future.sqlite3",
            DatabaseIdentity(uuid4().hex, "project", "project"),
        ),
    )
    SchemaManager().initialize(database, (future,))
    repo = SQLiteExecutionRepository(database, "project")
    assert not repo.current().complete
    assert repo.readiness().reason == "database_schema_unsupported"


@pytest.mark.parametrize(
    "path",
    [
        "../status.json",
        "C:/status.json",
        "/status.json",
        "a\\status.json",
        "a/./status.json",
        "a//status.json",
        "a\x00b",
    ],
)
def test_import_provenance_containment(isolated_path: Path, path: str) -> None:
    h = make_harness(isolated_path, importing=True)
    with pytest.raises(ValueError, match="invalid import provenance"):
        with h.database.transaction() as session:
            h.repo.import_legacy(
                session,
                (historical("task"),),
                source_facts=((path, "sha256:" + "a" * 64, "sha256:" + "b" * 64),),
                next_attempt_floors=(),
            )
    cutover(h)
    assert h.repo.page_history().records == ()


def test_import_batch_limits_and_generation(isolated_path: Path) -> None:
    h = make_harness(isolated_path, importing=True)
    with pytest.raises(ValueError, match="invalid import batch"):
        import_batch(h, tuple(historical(f"task-{i}") for i in range(257)))
    with pytest.raises(ExecutionError, match="stale_generation"):
        import_batch(h, (replace(historical("task"), generation=0),))
    cutover(h)
    assert h.repo.page_history().records == ()


def test_terminal_commit_rolls_back_current_and_receipt_together(
    harness: Harness,
) -> None:
    start = harness.start()
    real_save = harness.repo._save

    def fail(session: SqlSession, record: ExecutionRecord) -> ExecutionRecord:
        real_save(session, record)
        raise RuntimeError("crash before receipt/checkpoint")

    with patch.object(harness.repo, "_save", side_effect=fail):
        with pytest.raises(RuntimeError):
            harness.finish(start)
    assert harness.repo.current().records == (start,)
    assert harness.repo.page_history().high_water == 0
    done = harness.finish(start)
    assert done.history_seq == 1 and harness.repo.current().records == ()


def test_same_receipt_concurrent_cas_is_one_revision(harness: Harness) -> None:
    start = harness.start()
    barrier = Barrier(2)

    def observe() -> ExecutionRecord:
        barrier.wait(timeout=5)
        return harness.repo.apply_observation(
            receipt(start, "process"), expected_revision=start.revision, generation=1
        )

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: observe(), range(2)))
    assert results[0] == results[1] and results[0].revision == 3


def test_late_old_exit_updates_only_old_attempt_without_reordering(
    harness: Harness,
) -> None:
    starting = harness.start()
    old = harness.repo.apply_observation(
        receipt(starting, "absence", tree_absent=True),
        expected_revision=2,
        generation=1,
    )
    new = harness.prepare()
    new = harness.repo.reserve_start(
        new.key, expected_revision=new.revision, generation=1, launch_token="c" * 32
    )
    improved = harness.repo.apply_observation(
        receipt(old, "exit", exit_code=7, tree_absent=True),
        expected_revision=old.revision,
        generation=1,
    )
    assert improved.outcome == "failed" and improved.history_seq == old.history_seq
    assert harness.repo.current().records == (new,)
    with pytest.raises(ExecutionError, match="stale_generation"):
        harness.repo.apply_observation(
            receipt(new, "process"), expected_revision=new.revision, generation=0
        )


def test_current_snapshot_while_archived_collection_writer(harness: Harness) -> None:
    terminal = harness.finish(harness.start("archived"))
    active = harness.start("active", token="c" * 32)
    barrier = Barrier(2)

    def collect() -> None:
        barrier.wait(timeout=5)
        harness.repo.record_collection(
            terminal.key,
            "collected",
            terminal.payload_json,
            expected_revision=terminal.revision,
            generation=1,
        )

    with ThreadPoolExecutor(max_workers=1) as pool:
        writer = pool.submit(collect)
        barrier.wait(timeout=5)
        observed = harness.repo.current()
        writer.result(timeout=5)
    assert observed.complete and observed.records == (active,)


def test_current_python_decode_overrun_is_unknown(
    harness: Harness, monkeypatch: pytest.MonkeyPatch
) -> None:
    import processforge_core.executions.sqlite_repository as module

    harness.start()
    original = module._record

    def delayed(row: SqlRow) -> ExecutionRecord:
        time.sleep(0.02)
        return original(row)

    monkeypatch.setattr(module, "_record", delayed)
    snapshot = harness.repo.current(deadline=time.monotonic() + 0.01)
    assert not snapshot.complete and not snapshot.readiness.ready
    assert snapshot.readiness.reason == "database_deadline_exceeded"
