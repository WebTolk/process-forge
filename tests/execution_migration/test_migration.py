"""Exercise real SQL import/cutover with deterministic injected host proof."""

from __future__ import annotations

import hashlib
import json
import os
import runpy
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


def collection_files(project: Path, status: Path, project_id: str) -> tuple[Path, Path]:
    """Write the metadata produced by a completed legacy collect."""
    state = json.loads(status.read_bytes())
    directory = status.parent / "attempts" / str(state["attempt"])
    directory.mkdir(parents=True, exist_ok=True)
    reference = {
        "path": (directory / "prepared-input.json").relative_to(project).as_posix(),
        "checksum": "sha256:" + "a" * 64,
    }
    state["prepared_input"] = reference
    status.write_text(json.dumps(state), encoding="utf-8")
    receipt = {
        "schema_version": 1,
        "identity": {
            "kind": "work",
            "project_id": project_id,
            "run_id": state["run_id"],
            "assignment_id": state["task_id"],
            "context_id": "old-context",
            "attempt": state["attempt"],
        },
        "prepared_input": reference,
        "outputs": [
            {
                "path": "old-report.md",
                "required": True,
                "status": "present",
                "checksum": "sha256:" + "b" * 64,
                "size": 10,
            }
        ],
    }
    receipt["receipt_id"] = (
        "sha256:" + hashlib.sha256(canonical_json(receipt).encode("utf-8")).hexdigest()
    )
    receipt_path = directory / "collection-receipt.json"
    complete_path = directory / "collection-complete.json"
    receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
    complete_path.write_text(
        json.dumps({"schema_version": 1, "receipt_id": receipt["receipt_id"]}),
        encoding="utf-8",
    )
    return receipt_path, complete_path


@pytest.mark.parametrize("completed", [False, True])
def test_collection_history_survives_cutover_and_resume(
    harness: Harness, completed: bool
) -> None:
    status = harness.status("task")
    receipt, complete = collection_files(harness.project, status, "exact-project")
    if not completed:
        complete.unlink()
    originals = {
        path: path.read_bytes() for path in (status, receipt, complete) if path.exists()
    }
    plan = harness.service.plan(harness.project)
    assert plan["status"] == "planned", plan
    # Resume after rows/checkpoint have committed, before verification/cutover.
    with patch.object(harness.service, "_verify", side_effect=InterruptedError):
        assert harness.apply(plan)["blocked"]
    assert harness.resume(plan)["status"] == "ready"
    record = harness.repository.load(ExecutionKey("exact-project", "run", "task", 1))
    assert record is not None and record.outcome == "completed"
    assert record.collection == ("collected" if completed else "pending")
    assert harness.resume(plan)["status"] == "ready"
    assert harness.repository.load(record.key) == record
    assert {path: path.read_bytes() for path in originals} == originals


@pytest.mark.parametrize("change", ["add", "remove", "rewrite"])
def test_collection_completion_is_frozen(harness: Harness, change: str) -> None:
    status = harness.status("task")
    _, complete = collection_files(harness.project, status, "exact-project")
    raw = complete.read_bytes()
    if change == "add":
        complete.unlink()
    plan = harness.service.plan(harness.project)
    if change == "remove":
        complete.unlink()
    else:
        complete.write_bytes(raw + b" ")
    assert harness.apply(plan)["error"]["code"] == "execution_manifest_changed"
    assert not harness.database.target.path.exists()


@pytest.mark.parametrize(
    "damage",
    [
        "invalid_json",
        "missing_receipt",
        "completion_id",
        "receipt_hash",
        "project_id",
        "run_id",
        "assignment_id",
        "attempt",
        "prepared_input",
    ],
)
def test_invalid_collection_never_becomes_accepted(
    harness: Harness, damage: str
) -> None:
    status = harness.status("task")
    receipt_path, complete = collection_files(harness.project, status, "exact-project")
    receipt = json.loads(receipt_path.read_bytes())
    if damage == "invalid_json":
        complete.write_bytes(b"{")
    elif damage == "missing_receipt":
        receipt_path.unlink()
    elif damage == "completion_id":
        complete.write_text(
            json.dumps({"schema_version": 1, "receipt_id": "sha256:" + "c" * 64}),
            encoding="utf-8",
        )
    else:
        if damage == "receipt_hash":
            receipt["outputs"] = []
        else:
            if damage == "prepared_input":
                receipt["prepared_input"]["checksum"] = "sha256:" + "c" * 64
            else:
                receipt["identity"][damage] = 2 if damage == "attempt" else "other"
            receipt.pop("receipt_id")
            receipt["receipt_id"] = (
                "sha256:"
                + hashlib.sha256(canonical_json(receipt).encode("utf-8")).hexdigest()
            )
            complete.write_text(
                json.dumps({"schema_version": 1, "receipt_id": receipt["receipt_id"]}),
                encoding="utf-8",
            )
        receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
    result = harness.service.plan(harness.project)
    expected = (
        "execution_source_invalid"
        if damage
        in {"invalid_json", "missing_receipt", "completion_id", "receipt_hash"}
        else "execution_identity_conflict"
    )
    assert result["blocked"] and result["error"]["code"] == expected, result
    assert not harness.database.target.path.exists()


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
    plan = harness.service.plan(harness.project)
    assert plan["status"] == "planned", plan
    assert plan["counts"]["imported"] == 0
    assert plan["counts"]["floor_only"] == plan["counts"]["import_units"] == 1
    assert not harness.database.target.path.exists()
    assert not harness.evidence.exists()
    result = harness.apply(plan)
    assert result["status"] == "ready" and result["checkpoint"] == 1, result
    for table in (
        "execution_attempts",
        "execution_heads",
        "execution_current",
        "execution_receipt_admissions",
    ):
        assert harness.scalar("SELECT count(*) FROM " + table) == 0
    assert harness.repository.current().complete
    assert harness.repository.current().records == ()
    assert harness.repository.page_history().records == ()
    assert harness.scalar("SELECT next_history_seq FROM execution_state") == 1
    assert harness.scalar("SELECT next_attempt FROM execution_allocation_floors") == 8
    assert harness.resume(plan)["status"] == "ready"
    record = harness.repository.allocate_attempt(
        "run",
        "task",
        canonical_json(payload("task", status="ready")),
        generation=1,
    )
    assert record.key.attempt == json.loads(record.payload_json)["attempt"] == 8
    assert harness.scalar("SELECT count(*) FROM execution_allocation_floors") == 0
    assert harness.scalar("SELECT next_attempt FROM execution_heads") == 9
    assert harness.repository.page_history().records == ()
    assert harness.repository.current().records == ()


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


@pytest.mark.parametrize("floor_only", [False, True])
def test_manifest_memory_and_result_size_are_bounded(
    harness: Harness, floor_only: bool
) -> None:
    for i in range(513):
        if floor_only:
            (harness.flow / f"runtime/agent-runs/run/task-{i:04}/attempts/7").mkdir(
                parents=True
            )
        else:
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
    assert plan["counts"]["snapshots"] == (0 if floor_only else 513)
    assert plan["counts"]["floor_only"] == (513 if floor_only else 0)
    assert plan["counts"]["import_units"] == 513
    assert not harness.evidence.exists()
    (harness.project.parent / "memory-evidence.json").write_text(
        json.dumps(
            {
                "snapshots": plan["counts"]["snapshots"],
                "floor_only": plan["counts"]["floor_only"],
                "peak_traced_bytes": peak,
                "seconds": time.monotonic() - started,
                "plan_bytes": len(canonical_json(plan).encode("utf-8")),
            }
        ),
        encoding="utf-8",
    )


@pytest.mark.parametrize(
    "heartbeat,outcome",
    [
        ({"status": "completed", "exit_code": 0}, "completed"),
        ({"status": "failed", "exit_code": -9}, "failed"),
        (
            {"status": "starting", "model": "m", "workspace_dirs": ["space/é"]},
            "cancelled",
        ),
    ],
)
def test_public_codex_heartbeat_preserved(
    harness: Harness, heartbeat: JsonObject, outcome: str
) -> None:
    path = harness.status("task", status=outcome)
    status = json.loads(path.read_bytes())
    status["driver_id"] = "codex-exec"
    path.write_text(json.dumps(status), encoding="utf-8")
    receipt = path.with_name("heartbeat.json")
    original = (json.dumps(heartbeat, ensure_ascii=False, indent=2) + "\n").encode()
    receipt.write_bytes(original)
    plan = harness.service.plan(harness.project)
    assert harness.apply(plan)["status"] == "ready"
    assert harness.resume(plan)["status"] == "ready"
    record = harness.repository.load(ExecutionKey("exact-project", "run", "task", 1))
    assert record is not None and record.outcome == outcome
    assert receipt.read_bytes() == original
    manifest = (
        (harness.evidence / "manifest.ndjson").read_text(encoding="utf-8").splitlines()
    )
    assert {
        "relative_path": receipt.relative_to(harness.project).as_posix(),
        "size": len(original),
        "sha256": "sha256:" + hashlib.sha256(original).hexdigest(),
    } in [json.loads(row) for row in manifest]


@pytest.mark.parametrize("driver", ["codex-exec", "test-echo-worker"])
def test_public_codex_heartbeat_preserved_after_reprepare(
    harness: Harness, driver: str
) -> None:
    path = harness.status("task", attempt=2, status="ready")
    status = json.loads(path.read_bytes()) | {"driver_id": driver}
    path.write_text(json.dumps(status), encoding="utf-8")
    receipt = path.with_name("heartbeat.json")
    original = b'{"status":"completed","exit_code":0}\n'
    receipt.write_bytes(original)

    plan = harness.service.plan(harness.project)
    assert harness.apply(plan)["status"] == "ready"
    record = harness.repository.load(ExecutionKey("exact-project", "run", "task", 2))
    assert record is not None and record.phase == "prepared" and record.outcome is None
    assert harness.scalar("SELECT count(*) FROM execution_attempts") == 1
    assert harness.scalar("SELECT next_attempt FROM execution_heads") == 3
    assert receipt.read_bytes() == original


@pytest.mark.parametrize(
    "name,change,error",
    [
        ("attempts/1/heartbeat.json", {}, "execution_source_invalid"),
        ("exit.json", {}, "execution_source_invalid"),
        ("process.json", {}, "execution_source_invalid"),
        ("heartbeat.json", {"driver_id": "other"}, "execution_source_invalid"),
        ("heartbeat.json", None, "execution_source_invalid"),
        ("heartbeat.json", {"run_id": "other"}, "execution_identity_conflict"),
        ("heartbeat.json", {"status": "running"}, "execution_activity_unknown"),
        ("heartbeat.json", {"status": "ready"}, "execution_activity_unknown"),
        (
            "heartbeat.json",
            {"status": "ready", "attempt": 2, "pid": 123},
            "execution_activity_unknown",
        ),
        (
            "heartbeat.json",
            {"status": "ready", "attempt": 2, "started_at": "2026-11-19T00:00:00Z"},
            "execution_activity_unknown",
        ),
    ],
)
def test_public_codex_heartbeat_requires_own_terminal_task(
    harness: Harness, name: str, change: JsonObject | None, error: str
) -> None:
    path = harness.status("task")
    if change is None:
        path.unlink()
    else:
        status = json.loads(path.read_bytes()) | {"driver_id": "codex-exec"} | change
        path.write_text(json.dumps(status), encoding="utf-8")
    receipt = path.parent / name
    receipt.parent.mkdir(parents=True, exist_ok=True)
    receipt.write_text('{"status":"completed","exit_code":0}', encoding="utf-8")
    result = harness.service.plan(harness.project, skip_terminal_invalid=True)
    assert result["error"]["code"] == error
    assert not harness.database.target.path.exists()


@pytest.mark.parametrize(
    "heartbeat",
    [
        {"status": "failed", "exit_code": 0},
        {"status": "completed", "exit_code": True},
        {"status": "completed", "exit_code": 0, "run_id": "foreign"},
        {"schema_version": None, "status": "completed", "exit_code": 0},
        {"schema_version": 2, "status": "completed", "exit_code": 0},
        {"status": "starting", "model": "m", "workspace_dirs": [7]},
        {"status": "starting", "model": 1, "workspace_dirs": []},
        {"status": "starting", "model": "", "workspace_dirs": []},
    ],
)
def test_unrecognized_codex_heartbeat_blocks(
    harness: Harness, heartbeat: JsonObject
) -> None:
    path = harness.status("task")
    status = json.loads(path.read_bytes()) | {"driver_id": "codex-exec"}
    path.write_text(json.dumps(status), encoding="utf-8")
    path.with_name("heartbeat.json").write_text(json.dumps(heartbeat), encoding="utf-8")
    result = harness.service.plan(harness.project, skip_terminal_invalid=True)
    assert result["error"]["code"] == "execution_source_invalid"


def test_codex_fallback_versions_new_heartbeat(harness: Harness) -> None:
    worker = Path(__file__).resolve().parents[2] / "tools/codex_exec_worker.py"
    path = harness.flow / "heartbeat.json"
    runpy.run_path(str(worker))["write_heartbeat"](path, "completed", {"exit_code": 0})
    assert json.loads(path.read_bytes()) == {
        "schema_version": 1,
        "status": "completed",
        "exit_code": 0,
    }


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


@pytest.mark.parametrize("snapshots", [0, 129])
def test_mixed_floor_batches_are_bounded_and_replay_exact(
    harness: Harness,
    snapshots: int,
) -> None:
    for i in range(257):
        task = f"task-{i:04}"
        if i < snapshots:
            source = harness.status(task, attempt=3)
            root = source.parent
        else:
            root = harness.flow / "runtime/agent-runs/run" / task
        (root / "attempts/7").mkdir(parents=True)
    plan = harness.service.plan(harness.project)
    assert plan["status"] == "planned", plan
    assert plan["counts"]["import_units"] == 257
    assert plan["counts"]["floor_only"] == 257 - snapshots
    original = harness.repository.import_legacy
    batches = []

    def observed(
        session: SqlSession,
        records: tuple[ExecutionRecord, ...],
        *,
        source_facts: tuple[tuple[str, str, str], ...],
        next_attempt_floors: tuple[tuple[str, str, int], ...],
    ) -> tuple[int, int]:
        assert len(records) == len(source_facts) <= len(next_attempt_floors) <= 256
        before = harness.service._marker(session)
        result = original(
            session,
            records,
            source_facts=source_facts,
            next_attempt_floors=next_attempt_floors,
        )
        assert before is not None
        batches.append((len(records), len(next_attempt_floors), result))
        return result

    with patch.object(harness.repository, "import_legacy", side_effect=observed):
        result = harness.apply(plan)
    assert result["status"] == "ready" and result["checkpoint"] == 257, result
    assert [size for _, size, _ in batches] == [256, 1, 256, 1]
    assert sum(result[0] for _, _, result in batches) == snapshots
    assert harness.scalar("SELECT count(*) FROM execution_attempts") == snapshots
    assert harness.scalar("SELECT count(*) FROM execution_heads") == snapshots
    assert (
        harness.scalar("SELECT count(*) FROM execution_allocation_floors")
        == 257 - snapshots
    )
    assert (
        harness.scalar(
            "SELECT count(*) FROM execution_allocation_floors WHERE next_attempt<>8"
        )
        == 0
    )
    assert (
        harness.scalar("SELECT count(*) FROM execution_heads WHERE next_attempt<>8")
        == 0
    )
    assert harness.scalar("SELECT count(*) FROM execution_current") == 0
    assert len(harness.repository.page_history(limit=1000).records) == snapshots
    revision = harness.scalar("SELECT revision FROM execution_state")
    assert harness.resume(plan)["status"] == "ready"
    assert harness.scalar("SELECT revision FROM execution_state") == revision


def test_empty_record_batch_floor_and_checkpoint_rollback_together(
    harness: Harness,
) -> None:
    for i in range(257):
        (harness.flow / f"runtime/agent-runs/run/task-{i:04}/attempts/7").mkdir(
            parents=True
        )
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
        assert records == source_facts == ()
        result = original(
            session,
            records,
            source_facts=source_facts,
            next_attempt_floors=next_attempt_floors,
        )
        assert result == (0, 0)
        if calls == 2:
            raise MaintenanceError("fixture_floor_interruption")
        return result

    with patch.object(harness.repository, "import_legacy", side_effect=fail_second):
        assert harness.apply(plan)["error"]["code"] == "fixture_floor_interruption"
    assert harness.scalar("SELECT checkpoint FROM execution_migrations") == 256
    assert harness.scalar("SELECT count(*) FROM execution_allocation_floors") == 256
    assert harness.scalar("SELECT count(*) FROM execution_attempts") == 0
    assert harness.scalar("SELECT next_history_seq FROM execution_state") == 1
    assert harness.resume(plan)["status"] == "ready"
    assert harness.scalar("SELECT checkpoint FROM execution_migrations") == 257
    assert harness.scalar("SELECT count(*) FROM execution_allocation_floors") == 257


@pytest.mark.parametrize(
    "stage", ["_backup", "_initialize", "_import", "_verify", "_cutover", "_publish"]
)
def test_floor_only_crash_resume(harness: Harness, stage: str) -> None:
    (harness.flow / "runtime/agent-runs/run/task/attempts/7").mkdir(parents=True)
    plan = harness.service.plan(harness.project)
    with patch.object(harness.service, stage, side_effect=InterruptedError("fixture")):
        assert harness.apply(plan)["blocked"]
    assert harness.resume(plan)["status"] == "ready"
    assert harness.scalar("SELECT count(*) FROM execution_attempts") == 0
    assert harness.scalar("SELECT next_attempt FROM execution_allocation_floors") == 8
    assert (
        harness.repository.current().records
        == harness.repository.page_history().records
        == ()
    )


@pytest.mark.parametrize("change", ["add-lower", "remove", "rename"])
@pytest.mark.parametrize("resuming", [False, True])
def test_floor_directory_names_are_frozen_even_when_max_unchanged(
    harness: Harness,
    change: str,
    resuming: bool,
) -> None:
    root = harness.flow / "runtime/agent-runs/run/task/attempts"
    (root / "7").mkdir(parents=True)
    (root / "3").mkdir()
    plan = harness.service.plan(harness.project)
    if resuming:
        with patch.object(
            harness.service, "_cutover", side_effect=InterruptedError("fixture")
        ):
            assert harness.apply(plan)["blocked"]
    if change == "add-lower":
        (root / "2").mkdir()
    elif change == "remove":
        (root / "3").rmdir()
    else:
        (root / "3").rename(root / "4")
    result = harness.resume(plan) if resuming else harness.apply(plan)
    assert result["error"]["code"] == "execution_manifest_changed"
    if resuming:
        assert not harness.repository.readiness().ready
    else:
        assert not harness.database.target.path.exists()


@pytest.mark.parametrize("verdict", ["active", "unknown"])
def test_missing_status_is_not_quiescence_proof(
    harness: Harness, verdict: Literal["active", "unknown"]
) -> None:
    (harness.flow / "runtime/agent-runs/run/task/attempts/7").mkdir(parents=True)
    plan = harness.service.plan(harness.project)
    harness.verdict = verdict
    assert (
        harness.service.plan(harness.project)["error"]["code"]
        == "execution_activity_unknown"
    )
    result = harness.apply(plan)
    assert result["error"]["code"] == "execution_activity_unknown"
    assert not harness.database.target.path.exists()
    assert not (harness.flow / "data/execution-storage.json").exists()


@pytest.mark.parametrize(
    "mutation",
    [
        "DELETE FROM execution_allocation_floors",
        "UPDATE execution_allocation_floors SET next_attempt=7",
        "UPDATE execution_allocation_floors SET next_attempt=9",
    ],
)
def test_verification_refuses_floor_drift_before_replay(
    harness: Harness, mutation: str
) -> None:
    (harness.flow / "runtime/agent-runs/run/task/attempts/7").mkdir(parents=True)
    plan = harness.service.plan(harness.project)
    verify = harness.service._verify

    def corrupt(plan: JsonObject, evidence: Path) -> None:
        with harness.database.transaction() as session:
            session.execute(SqlStatement(mutation))
        verify(plan, evidence)

    with patch.object(harness.service, "_verify", side_effect=corrupt):
        result = harness.apply(plan)
    assert result["error"]["code"] == "execution_floor_verification_failed"
    assert not harness.repository.readiness().ready


def test_floor_only_manifest_never_opens_missing_history_bodies(
    harness: Harness,
) -> None:
    root = harness.flow / "runtime/agent-runs/run/é/attempts/7"
    root.mkdir(parents=True)
    names = {
        "prepared-input.json",
        "report.md",
        "status.json",
        "stdout.log",
        "stderr.log",
    }
    for name in names:
        (root / name).write_bytes(b"PRIVATE UNREADABLE HISTORY")
    opened = Path.open

    def guarded(
        path: Path,
        mode: str = "r",
        buffering: int = -1,
        encoding: str | None = None,
        errors: str | None = None,
        newline: str | None = None,
    ) -> IO[str] | IO[bytes]:
        if path.parent == root and path.name in names:
            pytest.fail("directory-only body reconstruction")
        return opened(path, mode, buffering, encoding, errors, newline)

    with patch.object(Path, "open", guarded):
        plan = harness.service.plan(harness.project)
        assert harness.apply(plan)["status"] == "ready"
    assert harness.repository.load_latest("run", "é") is None
    facts = [
        json.loads(line)
        for line in (harness.evidence / "manifest.ndjson")
        .read_text(encoding="utf-8")
        .splitlines()
    ]
    assert facts[-1]["allocation_floor"] == {
        "run_id": "run",
        "task_id": "é",
        "next_attempt": 8,
    }


def test_quarantined_snapshot_retains_its_allocation_floor(harness: Harness) -> None:
    source = harness.status("task", attempt=9)
    body = json.loads(source.read_bytes())
    del body["driver_id"]
    source.write_text(json.dumps(body), encoding="utf-8")
    original = source.read_bytes()
    plan = harness.service.plan(harness.project, skip_terminal_invalid=True)
    assert plan["counts"]["skipped"] == plan["counts"]["floor_only"] == 1
    assert harness.apply(plan)["status"] == "ready"
    assert source.read_bytes() == original
    assert harness.scalar("SELECT count(*) FROM execution_attempts") == 0
    assert harness.scalar("SELECT next_attempt FROM execution_allocation_floors") == 10
