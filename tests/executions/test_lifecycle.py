"""Crash gaps, uncertainty, collection, stale receipts and process identity."""

from __future__ import annotations

import json
import os
import socket
from dataclasses import replace
from pathlib import Path
from typing import Literal

import pytest

from processforge_core.executions.model import ExecutionError, ExecutionObservation
from processforge_core.executions.service import ExecutionService
from processforge_core.runtime import process_identity

from .test_repository import (
    PROCESS,
    STAMP,
    Harness,
    receipt,
)
from .test_repository import (
    harness as harness,
)
from .test_repository import (
    isolated_path as isolated_path,
)


def test_controller_death_and_exit_without_tree_proof_stay_current(
    harness: Harness,
) -> None:
    starting = harness.start()
    # No TTL reclamation: losing the controller before Popen/attach stays current.
    assert harness.repo.current().records == (starting,)
    service = ExecutionService(harness.repo)
    running = service.observe(
        receipt(starting, "process"), expected_revision=2, generation=1
    )
    unresolved = service.observe(
        receipt(running, "exit", exit_code=0), expected_revision=3, generation=1
    )
    assert unresolved.phase == "unresolved" and len(harness.repo.current().records) == 1
    assert service.payload(unresolved)["status"] == "running"
    absent = service.observe(
        receipt(unresolved, "absence", tree_absent=True),
        expected_revision=4,
        generation=1,
    )
    assert absent.outcome == "completed" and harness.repo.current().records == ()
    assert absent.history_seq == 1


def test_untrustworthy_exit_does_not_invent_success(harness: Harness) -> None:
    starting = harness.start()
    absent = harness.repo.apply_observation(
        receipt(starting, "absence", tree_absent=True),
        expected_revision=2,
        generation=1,
    )
    assert absent.outcome == "unknown_exit"
    assert (
        json.loads(absent.payload_json)["status"] == "unknown_exit"
    )  # Existing adapter status.
    assert json.loads(absent.payload_json)["exit_code"] is None


def test_unattached_absence_and_spawn_failure(harness: Harness) -> None:
    record = harness.start()
    with pytest.raises(ExecutionError, match="execution_activity_unknown"):
        harness.repo.apply_observation(
            receipt(record, "absence", process=None, tree_absent=True),
            expected_revision=2,
            generation=1,
        )
    with pytest.raises(ExecutionError, match="execution_activity_unknown"):
        harness.repo.apply_observation(
            receipt(record, "spawn_failed", process=None),
            expected_revision=2,
            generation=1,
        )
    absent = harness.repo.apply_observation(
        receipt(record, "spawn_failed", process=None, tree_absent=True),
        expected_revision=2,
        generation=1,
    )
    assert (
        absent.outcome == "failed"
        and absent.process is None
        and absent.history_seq == 1
    )
    assert harness.repo.current().records == ()


def test_heartbeat_timestamp_is_evidence_not_observation_clock(
    harness: Harness,
) -> None:
    record = harness.start()
    first = harness.repo.apply_observation(
        receipt(record, "heartbeat", 10), expected_revision=2, generation=1
    )
    second = harness.repo.apply_observation(
        receipt(first, "heartbeat", 11, observed_at="2026-10-24T15:59:00+00:00"),
        expected_revision=3,
        generation=1,
    )
    assert json.loads(second.payload_json)["last_heartbeat_at"] == STAMP
    old = harness.repo.apply_observation(
        receipt(second, "heartbeat", 9), expected_revision=1, generation=1
    )
    assert old == second


def test_collection_refusal_failure_replay_do_not_revive(harness: Harness) -> None:
    done = harness.finish(harness.start())
    refused = harness.repo.record_collection(
        done.key,
        "refused",
        done.payload_json,
        expected_revision=done.revision,
        generation=1,
    )
    assert refused.outcome == "completed"
    assert json.loads(refused.payload_json)["status"] == "completed"
    failed = harness.repo.record_collection(
        done.key,
        "failed",
        refused.payload_json,
        expected_revision=refused.revision,
        generation=1,
    )
    assert json.loads(failed.payload_json)["status"] == "failed"
    assert harness.repo.current().records == ()
    with pytest.raises(ExecutionError, match="stale_revision"):
        harness.repo.record_collection(
            done.key,
            "collected",
            done.payload_json,
            expected_revision=done.revision,
            generation=1,
        )
    late = harness.repo.apply_observation(
        receipt(failed, "heartbeat", 5), expected_revision=failed.revision, generation=1
    )
    assert late.phase == "absent" and late.history_seq == done.history_seq
    assert harness.repo.current().records == ()


def test_pid_birth_mismatch_never_attaches(harness: Harness) -> None:
    start = harness.start()
    attached = harness.repo.apply_observation(
        receipt(start, "process"), expected_revision=2, generation=1
    )
    for kind in ("exit", "heartbeat", "absence"):
        observation = ExecutionObservation(
            attached.key,
            attached.launch_token or "",
            kind,
            0,
            "sha256:" + "c" * 64,
            replace(PROCESS, birth_id="replacement"),
            STAMP,
            tree_absent=True,
        )
        with pytest.raises(ExecutionError, match="execution_identity_conflict"):
            harness.repo.apply_observation(
                observation, expected_revision=3, generation=1
            )
    assert harness.repo.current().records == (attached,)


def test_real_os_birth_and_tree_cannot_be_inferred() -> None:
    current = process_identity.capture_process(os.getpid())
    assert current is not None and current.birth_id
    assert process_identity.probe_process(current) == "same"
    assert process_identity.tree_absence(current) is False
    reused = replace(current, birth_id="old-incarnation", tree_id="verified-owned-tree")
    assert process_identity.probe_process(reused) == "absent"
    assert process_identity.tree_absence(reused) is None
    assert (
        process_identity.tree_absence(reused, owned_tree_probe=lambda _: False) is False
    )
    assert (
        process_identity.tree_absence(reused, owned_tree_probe=lambda _: True) is True
    )
    assert (
        process_identity.probe_process(replace(current, host_id="foreign-host"))
        == "unknown"
    )


def test_denied_process_probe_remains_unknown(monkeypatch: pytest.MonkeyPatch) -> None:
    def denied(pid: int, *, tree_id: str | None = None) -> None:
        raise ExecutionError("execution_activity_unknown")

    monkeypatch.setattr(process_identity, "capture_process", denied)
    identity = replace(PROCESS, host_id=socket.gethostname())
    assert process_identity.probe_process(identity) == "unknown"
    assert (
        process_identity.tree_absence(identity, owned_tree_probe=lambda _: True) is None
    )


def test_linux_parser_handles_comm_parentheses(monkeypatch: pytest.MonkeyPatch) -> None:
    def text(path: Path, encoding: str) -> str:
        if path.name == "boot_id":
            return "boot-identity\n"
        return "123 (worker (odd name)) S " + " ".join(["0"] * 18 + ["56789", "0", "0"])

    monkeypatch.setattr(Path, "read_text", text)
    observed = process_identity._linux_identity(123, "host", None)
    assert observed is not None
    assert (
        observed.birth_id == "linux-start-ticks:56789"
        and observed.boot_id == "boot-identity"
    )


def test_private_prepared_finalization_and_stale_cas(harness: Harness) -> None:
    from processforge_core.executions.projection import canonical_json

    from .test_repository import payload

    template = json.loads(payload())
    template["status"] = "planned"
    planned = harness.repo.allocate_attempt(
        "run", "task", canonical_json(template), generation=1
    )
    ready_payload = dict(
        template,
        status="ready",
        prepared_input={
            "path": "attempts/1/prepared-input.json",
            "checksum": "sha256:" + "a" * 64,
        },
    )
    ready = harness.repo._finalize_prepared(planned, canonical_json(ready_payload))
    assert ready.revision == 2 and ready.phase == "prepared"
    assert not harness.repo.current().records and ready.history_seq is None
    with pytest.raises(ExecutionError, match="stale_revision"):
        harness.repo._finalize_prepared(planned, canonical_json(ready_payload))
    with pytest.raises(ExecutionError, match="execution_activity_unknown"):
        harness.repo._finalize_prepared(ready, canonical_json(ready_payload))


@pytest.mark.parametrize("collection", ["collected", "failed", "refused"])
def test_private_manual_collection_never_invents_execution(
    harness: Harness, collection: Literal["collected", "failed", "refused"]
) -> None:
    from processforge_core.executions.projection import (
        canonical_json,
        projected_payload,
    )

    from .test_repository import payload

    manual = json.loads(payload())
    manual["status"] = "manual_required"
    record = harness.repo.allocate_attempt(
        "run", "task", canonical_json(manual), generation=1
    )
    changed = harness.repo._collect_manual(record, collection)
    assert changed.collection == collection and changed.phase == "prepared"
    assert (
        changed.outcome
        is changed.history_seq
        is changed.launch_token
        is changed.process
        is None
    )
    assert projected_payload(changed)["status"] == (
        "failed" if collection == "failed" else "manual_required"
    )
    assert harness.repo.current().records == ()
    assert harness.repo.page_history().records == ()
    with pytest.raises(ExecutionError, match="stale_revision"):
        harness.repo._collect_manual(record, collection)


@pytest.mark.parametrize("status", ["ready", "manual_required"])
def test_private_cancel_before_reservation_has_no_physical_history(
    harness: Harness, status: str
) -> None:
    from processforge_core.executions.projection import (
        canonical_json,
        projected_payload,
    )

    from .test_repository import payload

    template = json.loads(payload())
    template["status"] = status
    record = harness.repo.allocate_attempt(
        "run", "task", canonical_json(template), generation=1
    )
    cancelled = harness.repo._update_unlaunched(
        record, status="cancelled", reason="stop requested", finished_at=STAMP
    )
    assert (
        cancelled.phase == "prepared"
        and projected_payload(cancelled)["status"] == "cancelled"
    )
    assert cancelled.history_seq is cancelled.outcome is cancelled.launch_token is None
    assert harness.repo.current().records == harness.repo.page_history().records == ()
    with pytest.raises(ExecutionError, match="execution_activity_unknown"):
        harness.repo.reserve_start(
            cancelled.key,
            expected_revision=cancelled.revision,
            generation=1,
            launch_token="f" * 32,
        )


@pytest.mark.parametrize("descendant", [False, True])
def test_native_wrapper_authenticated_tree_receipts(
    isolated_path: Path, descendant: bool
) -> None:
    import hashlib
    import subprocess
    import sys
    import time
    from uuid import uuid4

    import prepared_executor
    import processforge as core

    from processforge_core.executions.projection import canonical_json

    from .test_repository import make_harness, payload

    root = isolated_path
    attempt = root / ".pf/runtime/agent-runs/run/task/attempts/1"
    attempt.mkdir(parents=True)
    document = {
        "schema_version": 1,
        "kind": "pf.prepared-input",
        "project_root": str(root),
        "identity": {
            "project_id": "project",
            "run_id": "run",
            "assignment_id": "task",
            "context_id": "context",
            "attempt": 1,
        },
        "input": {},
    }
    manifest = attempt / "prepared-input.json"
    raw = canonical_json(document).encode()
    manifest.write_bytes(raw)
    digest = "sha256:" + hashlib.sha256(raw).hexdigest()
    token = uuid4().hex
    environment = dict(os.environ)
    for name in ("PF_CONFIGURATION_SNAPSHOT_PATH", "PF_CONFIGURATION_SNAPSHOT_SHA256"):
        environment.pop(name, None)
    environment.update(
        PF_PROJECT_ROOT=str(root),
        PF_WORKER_RUN_ID="run",
        PF_WORKER_TASK_ID="task",
        PF_WORKER_ATTEMPT="1",
        PF_PREPARED_INPUT_FILE=str(manifest),
        PF_PREPARED_INPUT_SHA256=digest,
    )
    environment.update(
        dict(
            zip(
                prepared_executor._LAUNCH_ENV,
                ("project", "run", "task", "1", token),
                strict=True,
            )
        )
    )
    script = "import time; time.sleep(0.2)"
    if descendant:
        script = "import subprocess,sys; subprocess.Popen([sys.executable, '-B', '-c', 'import time; time.sleep(5)'])"
    wrapper = Path(prepared_executor.__file__)
    argv = [
        sys.executable,
        "-B",
        str(wrapper),
        "--prepared-input",
        str(manifest),
        "--prepared-sha256",
        digest,
        "--heartbeat",
        str(attempt / "heartbeat.json"),
        "--exit-path",
        str(attempt / "exit.json"),
        "--",
        sys.executable,
        "-B",
        "-c",
        script,
    ]
    with (
        (attempt / "wrapper.stdout").open("wb") as stdout,
        (attempt / "wrapper.stderr").open("wb") as stderr,
    ):
        child = subprocess.Popen(
            argv,
            env=environment,
            stdout=stdout,
            stderr=stderr,
            start_new_session=(os.name != "nt"),
        )
        try:
            if descendant:
                time.sleep(2.5)
                assert child.poll() is None
                assert not (attempt / "exit.json").exists()
            assert child.wait(timeout=12) == 0, (attempt / "wrapper.stderr").read_text()
        finally:
            if child.poll() is None:
                child.kill()
                child.wait()
    hroot = root / "sql"
    hroot.mkdir()
    harness = make_harness(hroot)
    template = json.loads(payload())
    template["heartbeat_path"] = (
        (attempt / "heartbeat.json").relative_to(root).as_posix()
    )
    prepared = harness.repo.allocate_attempt(
        "run", "task", canonical_json(template), generation=1
    )
    reserved = harness.repo.reserve_start(
        prepared.key, expected_revision=1, generation=1, launch_token=token
    )
    attached = core._sql_receipt(root, attempt / "process.json", reserved, "process")
    assert attached is not None and attached.process is not None
    # Windows venv launchers may delegate to a different native Python PID.
    assert attached.process.pid > 0 and attached.process.birth_id
    record = harness.repo.apply_observation(attached, expected_revision=2, generation=1)
    exit_receipt = core._sql_receipt(root, attempt / "exit.json", record, "exit")
    assert exit_receipt is not None
    assert exit_receipt.exit_code == 0
    record = harness.repo.apply_observation(
        exit_receipt, expected_revision=record.revision, generation=1
    )
    assert record.phase == "unresolved" and harness.repo.current().records
    assert record.process is not None
    deadline = time.monotonic() + 5
    while (
        time.monotonic() < deadline
        and prepared_executor.owned_tree_absent(record.process) is not True
    ):
        time.sleep(0.02)
    assert prepared_executor.owned_tree_absent(record.process) is True
    receipt = json.loads((attempt / "heartbeat.json").read_bytes())
    receipt["attempt"] = 2
    (attempt / "heartbeat.json").write_text(canonical_json(receipt))
    with pytest.raises(ExecutionError, match="receipt_conflict"):
        core._sql_receipt(root, attempt / "heartbeat.json", record, "heartbeat")


@pytest.fixture
def sql_cli_fixture(isolated_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Real CLI/SQL/native I/O, with the upstream Work-context boundary isolated."""
    import argparse
    import sys
    from uuid import uuid4

    import processforge as core
    from pf_runtime import host

    from processforge_core.common.yaml_io import write_yaml_file
    from processforge_core.configuration import DeviceConfigurationSource
    from processforge_core.database import (
        Database,
        DatabaseIdentity,
        DatabaseTarget,
        SchemaManager,
        SQLiteDriver,
        SqlStatement,
    )
    from processforge_core.executions.schema import EXECUTION_SCHEMA
    from processforge_core.executions.sqlite_repository import SQLiteExecutionRepository
    from processforge_core.prepared import input as prepared_input
    from processforge_core.runtime.drivers import RuntimeDriverDefinitionPolicy
    from processforge_core.work import context
    from processforge_core.work.paths import WorkPaths

    root = isolated_path
    monkeypatch.setattr(
        DeviceConfigurationSource,
        "default_path",
        staticmethod(lambda: root / "device.yaml"),
    )
    flow = root / ".pf"
    flow.mkdir()
    write_yaml_file(flow / "process-forge.yaml", {"project": {"id": "project"}})
    store_id = uuid4().hex
    database = Database(
        SQLiteDriver(),
        DatabaseTarget(
            flow / "data/pf.sqlite3", DatabaseIdentity(store_id, "project", "project")
        ),
    )
    SchemaManager().initialize(database, (EXECUTION_SCHEMA,))
    with database.transaction() as session:
        session.execute(
            SqlStatement(
                "INSERT INTO execution_state VALUES(1,'project',1,'sql','ready','complete',0,1,NULL,NULL)"
            )
        )
    repository = SQLiteExecutionRepository(database, "project")
    core._core_common_json_io.json_write(
        flow / "data/execution-storage.json",
        {
            "schema_version": 1,
            "project_id": "project",
            "store_id": store_id,
            "profile_id": "project_main",
            "target_relative_path": "data/pf.sqlite3",
        },
    )
    task = {
        "id": "task",
        "run_id": "run",
        "title": "SQL fixture",
        "status": "running",
        "allowed_files": [".pf/artifacts/report.md"],
        "required_outputs": [
            {"id": "report", "path": ".pf/artifacts/report.md", "required": True}
        ],
        "expected_report": {"artifact": ".pf/artifacts/report.md"},
    }
    paths = WorkPaths()
    write_yaml_file(paths.assignment_document(root, "task"), task)
    write_yaml_file(
        paths.run_root(root, "run") / "run.yaml",
        {"process_execution": {}, "status": "running"},
    )
    identity = {
        "project_id": "project",
        "run_id": "run",
        "assignment_id": "task",
        "context_id": "fixture-context",
    }
    capsule = {"execution_contract": {"identity": identity}}
    write_yaml_file(core.assignment_capsule_path(root, "task"), capsule)
    semantic = {
        "identity": identity,
        "outputs": {
            "expected_report": task["expected_report"],
            "required_outputs": task["required_outputs"],
        },
        "resources": {"grants": {}},
    }
    monkeypatch.setattr(
        context, "validate_execution_contract", lambda *a, **k: {"status": "valid"}
    )
    monkeypatch.setattr(prepared_input, "semantic_input", lambda *a, **k: semantic)
    monkeypatch.setattr(
        core, "existing_capsule_status", lambda *a: ("fresh", "fixture-capsule")
    )
    monkeypatch.setattr(
        core._process_event_recorder, "emit_process_event", lambda *a, **k: {}
    )
    monkeypatch.setattr(core, "emit_worker_completion_event", lambda *a, **k: {})
    monkeypatch.setattr(
        host,
        "ingest_event",
        lambda *a: {"accepted": True, "chat_message_ids": ["fixture-message"]},
    )
    monkeypatch.setattr(
        core._worker_plan_validation_service, "subagent_outputs", lambda *a: []
    )
    driver = RuntimeDriverDefinitionPolicy().default_documents()["generic-shell"]
    driver["id"] = "fixture-shell"
    driver["security"]["require_explicit_executable"] = False
    driver["environment"]["inherit"] = False
    driver["environment"].setdefault("variables", {})["PYTHONDONTWRITEBYTECODE"] = "1"
    script = "import os,pathlib; p=pathlib.Path(os.environ['PF_PROJECT_ROOT'])/'.pf/artifacts/report.md'; p.parent.mkdir(parents=True,exist_ok=True); p.write_text('# fixture result',encoding='utf-8')"
    driver["command"] = {
        "executable": sys.executable,
        "args": ["-c", script],
        "model_args": [],
    }
    driver_path = flow / "runtime/fixture-driver.yaml"
    write_yaml_file(driver_path, driver)
    args = argparse.Namespace(
        project_root=str(root),
        task="task",
        driver=str(driver_path),
        executable=None,
        model=None,
        reasoning_effort=None,
        detach=False,
    )
    return root, repository, args, driver_path


def test_real_sql_cli_prepare_start_status_collect_and_replay(sql_cli_fixture, capsys):
    import processforge as core

    root, repository, args, _driver = sql_cli_fixture
    assert core.command_worker_run_prepare(args) == 0
    planned = repository.load_latest("run", "task")
    assert planned.phase == "prepared" and planned.revision == 2
    assert core.command_worker_run_start(args) == 0
    finished = repository.load_latest("run", "task")
    assert finished.phase == "absent" and finished.outcome == "completed"
    status = core._work_paths.worker_run(root, "run", "task")["status"]
    status.write_text('{"status":"running","attempt":999}')
    assert core.command_worker_run_status(args) == 0
    assert core.load_agent_run_state(root, "run", "task")["attempt"] == 1
    assert core.command_worker_run_collect(args) == 0
    assert repository.load_latest("run", "task").collection == "collected"
    assert core.command_worker_run_collect(args) == 0
    assert "COLLECTED:" in capsys.readouterr().out
    assert not repository.current().records


@pytest.mark.parametrize("cancel", [False, True])
def test_real_sql_cli_manual_collect_or_unlaunched_stop(
    sql_cli_fixture, cancel, capsys
):
    import processforge as core

    from processforge_core.common.yaml_io import write_yaml_file
    from processforge_core.runtime.drivers import RuntimeDriverDefinitionPolicy

    root, repository, args, driver_path = sql_cli_fixture
    driver = RuntimeDriverDefinitionPolicy().default_documents()["manual"]
    driver["id"] = "fixture-manual"
    write_yaml_file(driver_path, driver)
    assert core.command_worker_run_prepare(args) == 0
    if cancel:
        assert core.command_worker_run_stop(args) == 0
        assert core.command_worker_run_stop(args) == 0
        assert core.load_agent_run_state(root, "run", "task")["status"] == "cancelled"
    else:
        assert core.command_worker_run_start(args) == 0
        report = root / ".pf/artifacts/report.md"
        report.parent.mkdir(parents=True, exist_ok=True)
        report.write_text("manual report")
        assert core.command_worker_run_collect(args) == 0
        assert core.command_worker_run_collect(args) == 0
        assert repository.load_latest("run", "task").collection == "collected"
    record = repository.load_latest("run", "task")
    assert (
        record.phase == "prepared"
        and record.launch_token
        is record.process
        is record.outcome
        is record.history_seq
        is None
    )
    assert repository.current().records == repository.page_history().records == ()


@pytest.mark.parametrize("history,current", [(0, 0), (510, 3)])
def test_scale_tool_uses_actual_guard_routes(
    isolated_path: Path, history: int, current: int
) -> None:
    from smoke_worker_storage_scale import case

    result = case(isolated_path, history, current)
    assert result["running"] == current
    assert result["attempt_rows"] == 2 * current
    assert result["terminal_files_read"] == result["terminal_rows_visited"] == 0


def test_old_prepared_input_launches_without_new_native_grants(sql_cli_fixture):
    import processforge as core

    from processforge_core.executions.projection import canonical_json
    from processforge_core.prepared import input as prepared_input

    root, repository, args, _driver = sql_cli_fixture
    task = core._worker_assignment_service.load(root, "task")
    capsule = core.load_yaml_document(core.assignment_capsule_path(root, "task"))
    document = prepared_input.build(root, task, capsule, 1, core)
    assert "native_launch" not in document
    attempt_root = (
        core._work_paths.worker_run(root, "run", "task")["root"] / "attempts/1"
    )
    path = attempt_root / "prepared-input.json"
    reference = {
        "path": path.relative_to(root).as_posix(),
        "checksum": prepared_input.digest(prepared_input.encoded(document)),
    }
    prepared_input.write_once(path, document)
    original = path.read_bytes()
    driver = core._runtime_driver_selection_service.for_task(root, task, args.driver)
    command, paths = core._worker_command_builder.build(
        root, task, driver, attempt=1, prepared_input=reference
    )
    payload = core._agent_run_payload(root, task, driver, "ready", paths, 1)
    payload["prepared_input"] = reference
    repository.allocate_attempt("run", "task", canonical_json(payload), generation=1)
    core._core_common_json_io.json_write(paths["command"], command)
    assert core.command_worker_run_start(args) == 0
    assert repository.load_latest("run", "task").phase == "absent"
    assert (
        path.read_bytes() == original
        and not path.with_name("configuration.snapshot.json").exists()
    )


@pytest.mark.parametrize("denied", [False, True])
def test_native_sql_detached_stop_and_signal_failure(
    sql_cli_fixture, monkeypatch, denied
):
    import time

    import prepared_executor
    import processforge as core

    from processforge_core.common.yaml_io import write_yaml_file

    root, repository, args, driver_path = sql_cli_fixture
    driver = core.load_yaml_document(driver_path)
    driver["command"]["args"] = ["-c", "import time; time.sleep(20)"]
    write_yaml_file(driver_path, driver)
    assert core.command_worker_run_prepare(args) == 0
    args.detach = True
    assert core.command_worker_run_start(args) == 0
    deadline = time.monotonic() + 7
    while (
        repository.load_latest("run", "task").process is None
        and time.monotonic() < deadline
    ):
        assert core.command_worker_run_status(args) == 0
        time.sleep(0.02)
    record = repository.load_latest("run", "task")
    assert record.process is not None
    signal = prepared_executor.signal_owned_tree
    try:
        if denied:

            def reject(_process):
                raise prepared_executor.ExecutorError("execution_activity_unknown")

            monkeypatch.setattr(prepared_executor, "signal_owned_tree", reject)
        assert core.command_worker_run_stop(args) == (1 if denied else 0)
        stopped = repository.load_latest("run", "task")
        assert stopped.phase == "stopping" and repository.current().records
    finally:
        monkeypatch.setattr(prepared_executor, "signal_owned_tree", signal)
        if repository.load_latest("run", "task").phase != "absent":
            signal(record.process)
    deadline = time.monotonic() + 7
    while repository.current().records and time.monotonic() < deadline:
        core.command_worker_run_status(args)
        time.sleep(0.02)
    assert not repository.current().records
    assert repository.load_latest("run", "task").phase == "absent"


def test_sql_ambiguous_spawn_retains_committed_current(sql_cli_fixture, monkeypatch):
    import processforge as core

    root, repository, args, _driver = sql_cli_fixture
    assert core.command_worker_run_prepare(args) == 0

    def ambiguous(*args, **kwargs):
        raise OSError("fixture spawn ambiguity")

    monkeypatch.setattr(core.subprocess, "Popen", ambiguous)
    assert core.command_worker_run_start(args) == 1
    record = repository.load_latest("run", "task")
    assert record.phase == "starting" and record.launch_token is not None
    assert record.history_seq is None and repository.current().records == (record,)


def test_sql_collection_repairs_marker_before_sql_crash(sql_cli_fixture, monkeypatch):
    import processforge as core

    from processforge_core.database import DatabaseError

    root, repository, args, _driver = sql_cli_fixture
    assert (
        core.command_worker_run_prepare(args)
        == core.command_worker_run_start(args)
        == 0
    )
    original = core._sql_collection_locked

    def interrupted(*args, **kwargs):
        raise DatabaseError("database_io_failed")

    monkeypatch.setattr(core, "_sql_collection_locked", interrupted)
    assert core.command_worker_run_collect(args) == 1
    assert repository.load_latest("run", "task").collection == "pending"
    monkeypatch.setattr(core, "_sql_collection_locked", original)
    assert core.command_worker_run_collect(args) == 0
    assert repository.load_latest("run", "task").collection == "collected"


def test_native_stop_never_signals_a_foreign_host(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import prepared_executor

    from .test_repository import PROCESS

    monkeypatch.setattr(
        prepared_executor, "_kernel", lambda: pytest.fail("foreign host signal")
    )
    with pytest.raises(
        prepared_executor.ExecutorError, match="execution_activity_unknown"
    ):
        prepared_executor.signal_owned_tree(
            replace(
                PROCESS,
                host_id="foreign-host",
                tree_id="windows-job:Local\\pf-execution-" + "a" * 32,
            )
        )


@pytest.mark.skipif(os.name != "nt", reason="Windows Job qualification")
@pytest.mark.parametrize("detached", [False, True])
def test_real_legacy_cli_timeout_cleans_owned_grandchild(
    sql_cli_fixture, monkeypatch, detached
):
    import time

    import processforge as core

    from processforge_core.common.yaml_io import write_yaml_file
    from processforge_core.executions.composition import ExecutionStorage

    root, _repository, args, driver_path = sql_cli_fixture
    monkeypatch.setattr(
        core, "_execution_storage", lambda *a, **k: ExecutionStorage("legacy")
    )
    # M1 isolates process lifecycle from the separately pending host factory.
    monkeypatch.setattr(core, "_storage_first_write", lambda *a, **k: (None, None))
    driver = core.load_yaml_document(driver_path)
    driver["command"]["args"] = [
        "-c",
        "import subprocess,sys,time; subprocess.Popen(['cmd.exe','/d','/c',sys.executable,'-B','-c','import time;time.sleep(60)']);time.sleep(60)",
    ]
    driver["limits"]["timeout_seconds"] = 1
    write_yaml_file(driver_path, driver)
    assert core.command_worker_run_prepare(args) == 0
    args.detach = detached
    try:
        assert core.command_worker_run_start(args) == (0 if detached else 1)
        if detached:
            time.sleep(1.2)
            assert core.command_worker_run_status(args) == 0
        state = core.load_agent_run_state(root, "run", "task")
        assert state["status"] == "timed_out"
        assert core._legacy_tree_probe(root, "run", "task", state) is True
        assert core.command_worker_run_stop(args) == 0
    finally:
        # Exact receipt-bound cleanup only, even if an assertion failed.
        state = core.load_agent_run_state(root, "run", "task")
        if state.get("pid") is not None:
            core._legacy_tree_probe(root, "run", "task", state, stop=True)


@pytest.mark.parametrize("terminal_status", ["timed_out", "completed"])
def test_legacy_terminal_unknown_ownership_does_not_signal(
    sql_cli_fixture, monkeypatch, terminal_status
):
    import processforge as core

    from processforge_core.executions.composition import ExecutionStorage

    root, _repository, args, _driver = sql_cli_fixture
    monkeypatch.setattr(
        core, "_execution_storage", lambda *a, **k: ExecutionStorage("legacy")
    )
    # M1 isolates process lifecycle from the separately pending host factory.
    monkeypatch.setattr(core, "_storage_first_write", lambda *a, **k: (None, None))
    assert core.command_worker_run_prepare(args) == 0
    paths = core._work_paths.worker_run(root, "run", "task")
    state = core.load_agent_run_state(root, "run", "task")
    state.update(status=terminal_status, pid=os.getpid(), failure_reason="timeout")
    core._core_common_json_io.json_write(paths["status"], state)
    task = core._worker_assignment_service.load(root, "task")
    assert core.existing_running_worker_run(root, task) is not None
    assert core.command_worker_run_stop(args) == 1
    assert core.load_agent_run_state(root, "run", "task")["status"] == "running"


def test_legacy_ambiguous_spawn_never_releases_ownership(sql_cli_fixture, monkeypatch):
    import pf_native_control
    import processforge as core

    from processforge_core.executions.composition import ExecutionStorage

    root, _repository, args, _driver = sql_cli_fixture
    monkeypatch.setattr(
        core, "_execution_storage", lambda *a, **k: ExecutionStorage("legacy")
    )
    monkeypatch.setattr(core, "_storage_first_write", lambda *a, **k: (None, None))
    assert core.command_worker_run_prepare(args) == 0

    def ambiguous(*args, **kwargs):
        raise OSError("fixture ambiguity")

    monkeypatch.setattr(pf_native_control, "spawn_owned", ambiguous)
    assert core.command_worker_run_start(args) == 1
    state = core.load_agent_run_state(root, "run", "task")
    assert state["status"] == "running" and state["pid"] is None
    assert state["failure_reason"] == "execution activity unknown"
    assert core.command_worker_run_prepare(args) == 0  # skipped, not reallocated
    assert core.load_agent_run_state(root, "run", "task")["attempt"] == state["attempt"]
    assert core.command_worker_run_stop(args) == 1


@pytest.mark.skipif(os.name != "nt", reason="Windows Job qualification")
def test_legacy_controller_crash_after_native_receipt_is_recoverable(
    sql_cli_fixture, monkeypatch
):
    import processforge as core

    from processforge_core.common.yaml_io import write_yaml_file
    from processforge_core.executions.composition import ExecutionStorage

    root, _repository, args, driver_path = sql_cli_fixture
    monkeypatch.setattr(
        core, "_execution_storage", lambda *a, **k: ExecutionStorage("legacy")
    )
    monkeypatch.setattr(core, "_storage_first_write", lambda *a, **k: (None, None))
    driver = core.load_yaml_document(driver_path)
    driver["command"]["args"] = ["-c", "import time;time.sleep(60)"]
    write_yaml_file(driver_path, driver)
    assert core.command_worker_run_prepare(args) == 0
    original = core.write_agent_run_state

    def interrupted(project, task, driver, status, **kwargs):
        if status == "running":
            raise RuntimeError("fixture controller publication crash")
        return original(project, task, driver, status, **kwargs)

    monkeypatch.setattr(core, "write_agent_run_state", interrupted)
    try:
        with pytest.raises(RuntimeError, match="fixture controller"):
            core.command_worker_run_start(args)
        monkeypatch.setattr(core, "write_agent_run_state", original)
        state = core.load_agent_run_state(root, "run", "task")
        assert state["status"] == "starting" and state["pid"] is None
        assert core.command_worker_run_status(args) == 0
        state = core.load_agent_run_state(root, "run", "task")
        assert state["status"] == "running" and type(state["pid"]) is int
        assert core.command_worker_run_stop(args) == 0
        assert core._legacy_tree_probe(root, "run", "task", state) is True
    finally:
        monkeypatch.setattr(core, "write_agent_run_state", original)
        core._legacy_tree_probe(
            root,
            "run",
            "task",
            core.load_agent_run_state(root, "run", "task"),
            stop=True,
        )


def test_legacy_guard_refuses_terminal_wrapper_without_tree_proof(
    sql_cli_fixture, monkeypatch
):
    import processforge as core

    from processforge_core.executions import composition
    from processforge_core.executions.composition import ExecutionStorage
    from processforge_core.runtime import metrics

    root, _repository, args, _driver = sql_cli_fixture
    monkeypatch.setattr(
        composition,
        "select_execution_storage",
        lambda *a, **k: ExecutionStorage("legacy"),
    )
    monkeypatch.setattr(core, "_storage_first_write", lambda *a, **k: (None, None))
    assert core.command_worker_run_prepare(args) == 0
    paths = core._work_paths.worker_run(root, "run", "task")
    state = core.load_agent_run_state(root, "run", "task")
    state.update(status="timed_out", pid=os.getpid(), failure_reason="timeout")
    core._core_common_json_io.json_write(paths["status"], state)
    result = metrics.observe(
        "workers",
        root / "workplace",
        [root],
        core,
        now=__import__("time").time(),
        coverage=True,
        budget=metrics.Budget(seconds=0.5),
    )
    assert result["counts"]["running"] is None
    assert result["coverage"] == "partial"


@pytest.mark.parametrize("operation", ["prepare", "start"])
@pytest.mark.parametrize("cancellation", [False, True])
def test_terminal_rejection_precedes_storage_and_provider(
    sql_cli_fixture, monkeypatch, capsys, operation, cancellation
):
    import subprocess

    import processforge as core

    from processforge_core.prepared import input as prepared_input
    from processforge_core.prepared import resources

    root, _repository, args, _driver = sql_cli_fixture
    task = core._worker_assignment_service.load(root, args.task)
    task.update(status="cancelled", process_execution={})
    monkeypatch.setattr(
        core._worker_assignment_service.__class__, "load", lambda *a: task
    )
    if cancellation:
        intent = root / ".pf/runs/run/cancellation-test.yaml"
        intent.parent.mkdir(parents=True, exist_ok=True)
        intent.write_text("pending\n")

    def forbidden(*args, **kwargs):
        raise AssertionError("rejected request reached a side effect")

    monkeypatch.setattr(core, "_storage_first_write", forbidden)
    monkeypatch.setattr(core, "prepare_worker_run", forbidden)
    monkeypatch.setattr(prepared_input, "load", forbidden)
    monkeypatch.setattr(resources, "native_start_preflight", forbidden)
    monkeypatch.setattr(subprocess, "Popen", forbidden)
    before = {p: p.read_bytes() for p in root.rglob("*") if p.is_file()}
    assert getattr(core, "command_worker_run_" + operation)(args) == 1
    assert (
        "cancellation_recovery_pending" if cancellation else "work_is_terminal"
    ) in capsys.readouterr().out
    assert {p: p.read_bytes() for p in root.rglob("*") if p.is_file()} == before


def test_real_missing_id_legacy_cli_prepare_start_and_retry(
    sql_cli_fixture, monkeypatch
):
    import argparse
    import shutil

    import processforge as core

    from processforge_core.common.yaml_io import write_yaml_file

    original, _repository, args, _driver = sql_cli_fixture
    root = original / "project"
    flow = root / ".pf"
    flow.mkdir(parents=True)
    write_yaml_file(flow / "process-forge.yaml", {"project": {"name": "old-shaped"}})
    for directory in ["assignments", "runs", "contexts", "runtime"]:
        source = original / ".pf" / directory
        if source.exists():
            shutil.copytree(source, flow / directory)
    legacy_args = argparse.Namespace(**vars(args))
    legacy_args.project_root = str(root)
    legacy_args.driver = str(flow / "runtime/fixture-driver.yaml")
    # The actual custom driver and prepared provider are shared by the existing
    # SQL fixture; no execution router or first-write coordinator is replaced.
    assert core._execution_storage(root).repository is None
    assert core.command_worker_run_prepare(legacy_args) == 0
    assert core.command_worker_run_start(legacy_args) == 0
    assert core.command_worker_run_prepare(legacy_args) == 0
    assert core.command_worker_run_start(legacy_args) == 0
    assert core._execution_storage(root).repository is None
    assert not (flow / "data/execution-storage.json").exists()
    assert not (flow / "data/pf.sqlite3").exists()
    assert "id" not in core._ProjectMetadataReader(root).manifest()["project"]


@pytest.mark.parametrize("failed", [False, True])
@pytest.mark.parametrize("artifact_only", [False, True])
def test_actual_managed_scratch_prepare_child_enduse_retry_collection(
    sql_cli_fixture, monkeypatch, failed, artifact_only
):
    """Exercise the actual ordinary SQL CLI and prepared executor, with a tiny child."""
    import processforge as core

    from processforge_core.common.yaml_io import write_yaml_file
    from processforge_core.prepared import input as prepared_input

    root, repository, args, driver_path = sql_cli_fixture
    (root / ".pf/tmp").mkdir()
    semantic = prepared_input.semantic_input(root, {}, {}, core)
    scope = {
        "allowed_files": [".pf/tmp/scratch-owned/**", ".pf/artifacts/report.md"],
        "allowed_read_files": [],
        "forbidden_files": [],
        "forbidden_actions": [],
        "allowed_actions": ["read", "write_product", "write_artifact"],
        "ownership": {
            "writer": True,
            "owner_id": "worker",
            "owned_files": [".pf/tmp/scratch-owned/**"],
        },
    }
    if artifact_only:
        scope["allowed_actions"] = ["read", "write_artifact"]
        scope["forbidden_actions"] = ["write_product"]
    original_scope = json.loads(json.dumps(scope))
    semantic["scope"] = scope
    semantic["sources"] = []
    driver = core.load_yaml_document(driver_path)
    script = "import os,pathlib,tempfile; temp=pathlib.Path(tempfile.gettempdir()); assert str(temp)==os.environ['PF_WORKER_SCRATCH']; (temp/'child.tmp').write_bytes(b'disposable'); p=pathlib.Path(os.environ['PF_PROJECT_ROOT'])/'.pf/artifacts/report.md'; p.parent.mkdir(parents=True,exist_ok=True); p.write_text('# fixture result',encoding='utf8')"
    driver["command"]["args"] = [
        "-B",
        "-c",
        script + ("; raise SystemExit(7)" if failed else ""),
    ]
    write_yaml_file(driver_path, driver)
    assert core.command_worker_run_prepare(args) == 0
    state = core.load_agent_run_state(root, "run", "task")
    doc = prepared_input.load(
        root, core._worker_assignment_service.load(root, "task"), state, core
    )
    scratch_root = root / doc["managed_scratch"]["path"]
    assert scratch_root.is_dir()
    assert doc["input"]["scope"] == original_scope
    assert core.command_worker_run_start(args) == (1 if failed else 0)
    record = repository.load_latest("run", "task")
    assert record.phase == "absent"
    if failed:
        assert record.outcome == "failed" and not scratch_root.exists()
        driver["command"]["args"] = ["-B", "-c", script]
        write_yaml_file(driver_path, driver)
        assert core.command_worker_run_prepare(args) == 0
        next_state = core.load_agent_run_state(root, "run", "task")
        assert next_state["attempt"] == state["attempt"] + 1
        retry_doc = prepared_input.load(
            root, core._worker_assignment_service.load(root, "task"), next_state, core
        )
        retry_root = root / retry_doc["managed_scratch"]["path"]
        assert retry_root != scratch_root and retry_root.is_dir()
        assert retry_doc["input"]["scope"] == original_scope
        assert core.command_worker_run_start(args) == 0
        assert (retry_root / "child.tmp").read_bytes() == b"disposable"
        assert core.command_worker_run_collect(args) == 0
        assert not retry_root.exists()
        retry_attempt = root / next_state["prepared_input"]["path"]
        retry_receipt = json.loads(
            retry_attempt.with_name("scratch-cleanup.json").read_bytes()
        )
        assert retry_receipt["result"] == "deleted"
        assert retry_receipt["deleted_files"] == 1
    else:
        assert (scratch_root / "child.tmp").read_bytes() == b"disposable"
        assert core.command_worker_run_collect(args) == 0
        assert not scratch_root.exists()
    attempt = root / state["prepared_input"]["path"]
    assert attempt.with_name("scratch-release.json").is_file()
    receipt = json.loads(attempt.with_name("scratch-cleanup.json").read_bytes())
    assert receipt["result"] == "deleted" and receipt["deleted_files"] == 1
