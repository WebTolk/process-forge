"""Exercise real SQL import/cutover with deterministic injected host proof."""

from __future__ import annotations

import json
import os
import time
import tracemalloc
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import IO, Literal
from unittest.mock import patch
from uuid import uuid4

import pytest

from processforge_core.database import (
    Database,
    DatabaseIdentity,
    DatabaseTarget,
    SchemaManager,
    SQLiteDriver,
    SqlSession,
    SqlStatement,
)
from processforge_core.executions.model import ExecutionKey, ExecutionRecord
from processforge_core.executions.projection import canonical_json
from processforge_core.executions.sqlite_repository import SQLiteExecutionRepository
from processforge_core.maintenance.backup import SQLiteBackupService
from processforge_core.maintenance.contracts import (
    ExecutionMigrationContext,
    JsonObject,
    MaintenanceError,
    MigrationSafety,
)
from processforge_core.maintenance.execution_migration import (
    MIGRATION_ID,
    ExecutionMigrationService,
)
from processforge_core.runtime.execution_admission import ExecutionAdmission


def payload(
    task: str, *, run: str = "run", attempt: int = 1, status: str = "completed"
) -> JsonObject:
    """Return the complete legacy compatibility DTO, with an opaque extension."""
    return {
        "schema_version": 1,
        "run_id": run,
        "task_id": task,
        "driver_id": "generic-shell",
        "agent_model": "",
        "status": status,
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
        "opaque": {"original": "é/ё"},
    }


@dataclass
class Harness:
    """Keep fixture paths, actual repository and observable fake admission/proof."""

    project: Path
    depth: int = 0
    generation: str = "host-epoch-1"
    verdict: Literal["proven", "active", "unknown"] = "proven"
    phases: list[str] = field(default_factory=list)
    database: Database = field(init=False)
    repository: SQLiteExecutionRepository = field(init=False)
    service: ExecutionMigrationService = field(init=False)

    def __post_init__(self) -> None:
        self.flow.mkdir(parents=True)
        (self.flow / "process-forge.yaml").write_text(
            "project:\n  id: exact-project\n", encoding="utf-8"
        )
        self.database = Database(
            SQLiteDriver(),
            DatabaseTarget(
                self.flow / "data/pf.sqlite3",
                DatabaseIdentity("a" * 32, "project", "exact-project"),
            ),
        )
        self.repository = SQLiteExecutionRepository(self.database, "exact-project")
        self.service = ExecutionMigrationService(
            database=self.database,
            repository=self.repository,
            admission=ExecutionAdmission(self.lock),
            backup=SQLiteBackupService(),
            safety=self.proof,
        )

    @property
    def flow(self) -> Path:
        return self.project / ".pf"

    @property
    def evidence(self) -> Path:
        return self.flow / "maintenance/execution/test"

    @contextmanager
    def lock(
        self, path: Path, *, timeout_seconds: float, stale_after_seconds: int
    ) -> Iterator[object]:
        assert timeout_seconds > 0 and stale_after_seconds == 0
        assert path.name == "execution-admission"
        self.depth += 1
        try:
            yield object()
        finally:
            self.depth -= 1

    def proof(self, context: ExecutionMigrationContext) -> MigrationSafety:
        assert context.project_root == self.project
        assert context.project_id == "exact-project" and context.store_id == "a" * 32
        assert context.target_relative_path == "data/pf.sqlite3"
        assert context.source_generation == 0 and context.target_generation == 1
        assert context.manifest_checksum.startswith("sha256:")
        assert self.depth == (0 if context.phase == "inspect" else 1)
        self.phases.append(context.phase)
        return MigrationSafety(
            self.verdict, self.generation, ("fixture:qualified-exclusion-and-trees",)
        )

    def status(
        self,
        task: str,
        *,
        run: str = "run",
        attempt: int = 1,
        status: str = "completed",
    ) -> Path:
        path = self.flow / "runtime/agent-runs" / run / task / "status.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(
                payload(task, run=run, attempt=attempt, status=status),
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        return path

    def apply(self, plan: JsonObject | None = None) -> JsonObject:
        return self.service.apply(
            self.project,
            plan or self.service.plan(self.project),
            evidence_dir=self.evidence,
            offline_confirmed=True,
        )

    def resume(self, plan: JsonObject) -> JsonObject:
        return self.service.resume(
            self.project,
            migration_id=MIGRATION_ID,
            plan_checksum=plan["plan_checksum"],
            evidence_dir=self.evidence,
            offline_confirmed=True,
        )

    def scalar(self, sql: str) -> object:
        with self.database.read() as session:
            row = session.fetch_one(SqlStatement(sql))
            assert row is not None
            return row[0]


@pytest.fixture
def harness() -> Harness:
    """Use an owned, inherited-permission directory; do not alter any ACL."""
    return Harness(Path(os.environ["PF_W4_TEST_ROOT"]) / uuid4().hex)


@pytest.mark.parametrize("count", [0, 1, 257])
def test_success_exact_bytes_and_one_cutover(harness: Harness, count: int) -> None:
    paths = [harness.status(f"task-{i:04}") for i in range(count)]
    originals = {p: p.read_bytes() for p in paths}
    plan = harness.service.plan(harness.project)
    assert plan["status"] == "planned", plan
    assert not harness.database.target.path.exists()
    assert not harness.evidence.exists()
    result = harness.apply(plan)
    assert result["status"] == "ready", result
    assert result["checkpoint"] == count
    assert harness.repository.readiness().ready
    assert (
        harness.repository.current().complete
        and harness.repository.current().records == ()
    )
    assert originals == {p: p.read_bytes() for p in originals}
    before = harness.scalar("SELECT revision FROM execution_state")
    assert harness.resume(plan)["status"] == "ready"
    assert harness.scalar("SELECT revision FROM execution_state") == before
    assert harness.scalar("SELECT count(*) FROM execution_attempts") == count
    assert harness.phases == ["inspect", "freeze", "cutover", "resume"]
    assert (harness.evidence / "verification/manifest.json").is_file()


def test_directory_floor_no_guessed_history(harness: Harness) -> None:
    path = harness.status("task", attempt=3)
    (path.parent / "attempts/19").mkdir(parents=True)
    (path.parent / "attempts/5").mkdir()
    (path.parent / "attempts/19/prepared-input.json").write_bytes(b"DO NOT READ")
    assert harness.apply()["status"] == "ready"
    assert harness.scalar("SELECT next_attempt FROM execution_heads") == 20
    assert harness.scalar("SELECT count(*) FROM execution_attempts") == 1
    record = harness.repository.load(ExecutionKey("exact-project", "run", "task", 3))
    assert record is not None and record.key.attempt == 3 and record.history_seq == 1
    assert json.loads(record.payload_json)["opaque"] == {"original": "é/ё"}


def test_directory_only_does_not_create_attempt(harness: Harness) -> None:
    (harness.flow / "runtime/agent-runs/run/task/attempts/7").mkdir(parents=True)
    assert (
        harness.service.plan(harness.project)["error"]["code"]
        == "execution_snapshot_required"
    )
    assert not harness.database.target.path.exists()


@pytest.mark.parametrize("name", ["01", "٠١", "0", "-1", "+1", "9223372036854775807"])
def test_ambiguous_directory_blocks(harness: Harness, name: str) -> None:
    path = harness.status("task")
    (path.parent / "attempts" / name).mkdir(parents=True)
    result = harness.service.plan(harness.project)
    assert result["error"]["code"] == "execution_attempt_directory_invalid"
    assert not harness.database.target.path.exists()


@pytest.mark.parametrize("bad", [None, True, 0, -1, "2", 1.0])
def test_invalid_or_missing_attempt_never_guessed(
    harness: Harness, bad: object
) -> None:
    path = harness.status("task")
    value = payload("task")
    value["attempt"] = bad
    path.write_text(json.dumps(value), encoding="utf-8")
    assert (
        harness.service.plan(harness.project)["error"]["code"]
        == "execution_attempt_required"
    )


@pytest.mark.parametrize(
    "raw",
    [
        b'{"schema_version":1,"schema_version":1}',
        b'{"x":NaN}',
        b'{"x":1e999}',
        b'{"x":"\\u0000"}',
        b"{",
        b"[]",
    ],
)
def test_strict_source_json(harness: Harness, raw: bytes) -> None:
    harness.status("task").write_bytes(raw)
    assert harness.service.plan(harness.project)["blocked"] is True


@pytest.mark.parametrize("status", ["starting", "running", "future"])
def test_unknown_current_cannot_skip(harness: Harness, status: str) -> None:
    harness.status("task", status=status)
    result = harness.service.plan(harness.project, skip_terminal_invalid=True)
    assert result["error"]["code"] == "execution_activity_unknown"


@pytest.mark.parametrize(
    "field,value",
    [
        ("schema_version", 2),
        ("task_id", "other"),
        ("run_id", "other"),
        ("project_id", "foreign"),
    ],
)
def test_schema_identity_conflicts_always_block(
    harness: Harness, field: str, value: object
) -> None:
    path = harness.status("task")
    body = payload("task")
    body[field] = value
    path.write_text(json.dumps(body), encoding="utf-8")
    assert harness.service.plan(harness.project, skip_terminal_invalid=True)["blocked"]


def test_skip_only_proved_historical_preserves_exact_quarantine(
    harness: Harness,
) -> None:
    path = harness.status("task")
    body = payload("task")
    del body["driver_id"]
    raw = json.dumps(body).encode()
    path.write_bytes(raw)
    assert harness.service.plan(harness.project)["blocked"]
    plan = harness.service.plan(harness.project, skip_terminal_invalid=True)
    assert plan["counts"]["skipped"] == 1
    assert harness.apply(plan)["status"] == "ready"
    assert raw in [p.read_bytes() for p in (harness.evidence / "sources").iterdir()]
    assert harness.scalar("SELECT count(*) FROM execution_attempts") == 0


@pytest.mark.parametrize("verdict", ["active", "unknown"])
def test_host_proof_not_operator_flag(
    harness: Harness, verdict: Literal["active", "unknown"]
) -> None:
    harness.verdict = verdict
    assert (
        harness.service.plan(harness.project)["error"]["code"]
        == "execution_activity_unknown"
    )
    harness.verdict = "proven"
    plan = harness.service.plan(harness.project)
    harness.verdict = verdict
    assert harness.apply(plan)["blocked"]
    assert not (harness.flow / "data/execution-storage.json").exists()


def test_no_proof_or_exception_fails_closed(harness: Harness) -> None:
    plan = harness.service.plan(harness.project)
    harness.service.safety = None
    assert harness.apply(plan)["error"]["code"] == "execution_safety_unavailable"
    with patch.object(
        harness.service, "safety", side_effect=RuntimeError("private secret")
    ):
        report = harness.apply(plan)
    assert "private secret" not in canonical_json(report)
    assert report["blocked"]


def test_changed_proof_under_cutover_keeps_pending(harness: Harness) -> None:
    harness.status("task")
    plan = harness.service.plan(harness.project)
    original = harness.service._verify

    def verify(*args: object) -> None:
        original(plan, harness.evidence)
        harness.generation = "changed-instance"

    with patch.object(harness.service, "_verify", side_effect=verify):
        result = harness.apply(plan)
    assert result["error"]["code"] == "execution_safety_changed"
    assert harness.scalar("SELECT authority FROM execution_state") == "legacy"
    harness.generation = "host-epoch-1"
    assert harness.resume(plan)["status"] == "ready"


def test_manifest_drift_before_freeze(harness: Harness) -> None:
    path = harness.status("task")
    plan = harness.service.plan(harness.project)
    path.write_bytes(path.read_bytes() + b" ")
    assert harness.apply(plan)["error"]["code"] == "execution_manifest_changed"
    assert not harness.database.target.path.exists()
    assert not (harness.flow / "data/execution-storage.json").exists()


@pytest.mark.parametrize(
    "stage", ["_backup", "_initialize", "_import", "_verify", "_cutover", "_publish"]
)
def test_interruption_and_exact_resume(harness: Harness, stage: str) -> None:
    harness.status("task")
    plan = harness.service.plan(harness.project)
    with patch.object(
        harness.service, stage, side_effect=InterruptedError("fixture stop")
    ):
        result = harness.apply(plan)
    assert result["blocked"]
    resumed = harness.resume(plan)
    assert resumed["status"] == "ready", resumed
    assert harness.scalar("SELECT count(*) FROM execution_attempts") == 1


def test_import_and_checkpoint_rollback_together(harness: Harness) -> None:
    for i in range(257):
        harness.status(f"task-{i:04}")
    plan = harness.service.plan(harness.project)
    original = harness.repository.import_legacy
    calls = 0

    def fail_second(
        session: SqlSession,
        records: tuple[ExecutionRecord, ...],
        *,
        source_facts: tuple[tuple[str, str, str], ...],
        next_attempt_floors: tuple[tuple[str, str, int], ...],
    ) -> tuple[int, int]:
        nonlocal calls
        calls += 1
        result = original(
            session,
            records,
            source_facts=source_facts,
            next_attempt_floors=next_attempt_floors,
        )
        if calls == 2:
            raise MaintenanceError("fixture_interruption")
        return result

    with patch.object(harness.repository, "import_legacy", side_effect=fail_second):
        result = harness.apply(plan)
    assert result["blocked"]
    assert harness.scalar("SELECT checkpoint FROM execution_migrations") == 256
    assert harness.scalar("SELECT count(*) FROM execution_attempts") == 256
    assert harness.resume(plan)["status"] == "ready"


def test_existing_envelope_verified_backup_reuse(harness: Harness) -> None:
    SchemaManager().initialize(harness.database, ())
    harness.status("task")
    plan = harness.service.plan(harness.project)
    with patch.object(harness.service, "_import", side_effect=InterruptedError()):
        assert harness.apply(plan)["blocked"]
    before = (harness.evidence / "backup/manifest.json").read_bytes()
    with patch.object(
        harness.service.backup, "create", wraps=harness.service.backup.create
    ) as create:
        assert harness.resume(plan)["status"] == "ready"
    assert [call.args[1].name for call in create.call_args_list] == ["verification"]
    assert (harness.evidence / "backup/manifest.json").read_bytes() == before


def test_corrupt_backup_blocks_resume(harness: Harness) -> None:
    SchemaManager().initialize(harness.database, ())
    plan = harness.service.plan(harness.project)
    with patch.object(harness.service, "_import", side_effect=InterruptedError()):
        assert harness.apply(plan)["blocked"]
    (harness.evidence / "backup/database.sqlite3").write_bytes(b"corrupt")
    assert harness.resume(plan)["blocked"]
    assert harness.scalar("SELECT authority FROM execution_state") == "legacy"


def test_replay_conflict_and_no_false_ready(harness: Harness) -> None:
    harness.status("task")
    plan = harness.service.plan(harness.project)
    with patch.object(harness.service, "_verify", side_effect=InterruptedError()):
        assert harness.apply(plan)["blocked"]
    with harness.database.transaction() as session:
        session.execute(
            SqlStatement(
                "UPDATE execution_attempts SET source_checksum=?",
                ("sha256:" + "b" * 64,),
            )
        )
    result = harness.resume(plan)
    assert result["error"]["code"] == "execution_identity_conflict"
    assert harness.scalar("SELECT authority FROM execution_state") == "legacy"


def test_explicit_abort_only_before_target_mutation(harness: Harness) -> None:
    plan = harness.service.plan(harness.project)
    with patch.object(harness.service, "_backup", side_effect=InterruptedError()):
        assert harness.apply(plan)["blocked"]
    result = harness.service.abort(
        harness.project,
        plan_checksum=plan["plan_checksum"],
        evidence_dir=harness.evidence,
        offline_confirmed=True,
    )
    assert result["phase"] == "aborted"
    assert not (harness.flow / "data/execution-storage.json").exists()
    assert not harness.database.target.path.exists()


def test_no_postcutover_rollback(harness: Harness) -> None:
    plan = harness.service.plan(harness.project)
    assert harness.apply(plan)["status"] == "ready"
    result = harness.service.abort(
        harness.project,
        plan_checksum=plan["plan_checksum"],
        evidence_dir=harness.evidence,
        offline_confirmed=True,
    )
    assert result["error"]["code"] == "execution_abort_unsafe"
    assert harness.repository.readiness().ready


def test_order_raw_utf8_and_no_output_prepared_reads(harness: Harness) -> None:
    for run in ["a", "a-b", "é", "ё"]:
        path = harness.status("task", run=run)
        for name in ["stdout.log", "stderr.log", "report.md", "prepared-input.json"]:
            (path.parent / name).write_bytes(b"PRIVATE BODY")
    opened = Path.open

    def guarded(
        path: Path,
        mode: str = "r",
        buffering: int = -1,
        encoding: str | None = None,
        errors: str | None = None,
        newline: str | None = None,
    ) -> IO[str] | IO[bytes]:
        if path.name in {
            "stdout.log",
            "stderr.log",
            "report.md",
            "prepared-input.json",
        }:
            pytest.fail("forbidden body read")
        return opened(path, mode, buffering, encoding, errors, newline)

    with patch.object(Path, "open", guarded):
        plan = harness.service.plan(harness.project)
        result = harness.apply(plan)
    assert result["status"] == "ready", result
    paths = [
        json.loads(line).get("relative_path")
        for line in (harness.evidence / "manifest.ndjson")
        .read_text(encoding="utf-8")
        .splitlines()
    ]
    assert paths == sorted(paths, key=lambda path: path.encode("utf-8"))
    assert [r.key.run_id for r in harness.repository.page_history().records] == [
        "a-b",
        "a",
        "é",
        "ё",
    ]


def test_project_move_preserves_relative_binding_and_identity(harness: Harness) -> None:
    harness.status("task")
    plan = harness.service.plan(harness.project)
    assert harness.apply(plan)["status"] == "ready"
    new = harness.project.with_name(harness.project.name + "-moved")
    harness.project.rename(new)
    harness.project = new
    harness.database.target = DatabaseTarget(
        harness.flow / "data/pf.sqlite3", harness.database.target.identity
    )
    assert harness.resume(plan)["status"] == "ready"
    assert harness.repository.readiness().store_id == "a" * 32


def test_manifest_memory_and_result_size_are_bounded(harness: Harness) -> None:
    for i in range(513):
        harness.status(f"task-{i:04}")
    tracemalloc.start()
    started = time.monotonic()
    try:
        plan = harness.service.plan(harness.project)
        _, peak = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()
    assert plan["status"] == "planned", plan
    assert peak < 8 * 1024 * 1024
    assert len(canonical_json(plan).encode("utf-8")) < 4096
    assert plan["counts"]["snapshots"] == 513
    assert not harness.evidence.exists()
    (harness.project.parent / "memory-evidence.json").write_text(
        json.dumps(
            {
                "snapshots": 513,
                "peak_traced_bytes": peak,
                "seconds": time.monotonic() - started,
                "plan_bytes": len(canonical_json(plan).encode("utf-8")),
            }
        ),
        encoding="utf-8",
    )


def test_all_inventory_paths_raw_sorted_including_attempt_receipts(
    harness: Harness,
) -> None:
    path = harness.status("task")
    for attempt in ["1", "10", "2"]:
        root = path.parent / "attempts" / attempt
        root.mkdir(parents=True)
        for name in ["process.json", "heartbeat.json", "exit.json"]:
            (root / name).write_text('{"schema_version":1}', encoding="utf-8")
    for name in ["process.json", "heartbeat.json", "exit.json"]:
        (path.parent / name).write_text('{"schema_version":1}', encoding="utf-8")
    assert harness.apply()["status"] == "ready"
    facts = [
        json.loads(line)
        for line in (harness.evidence / "manifest.ndjson")
        .read_text(encoding="utf-8")
        .splitlines()
    ]
    paths = [fact.get("relative_path", fact.get("directory")) for fact in facts]
    assert paths == sorted(paths, key=lambda value: value.encode("utf-8"))


def test_committed_resume_verifies_retained_integrity_snapshot(
    harness: Harness,
) -> None:
    plan = harness.service.plan(harness.project)
    assert harness.apply(plan)["status"] == "ready"
    (harness.evidence / "verification/database.sqlite3").write_bytes(b"tampered")
    assert harness.resume(plan)["blocked"]
    assert harness.repository.readiness().ready
