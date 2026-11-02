"""Real legacy prepare and collection proofs keep long reads outside admission."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

import processforge as core
import pytest
from pf_runtime import host

from processforge_core.common.yaml_io import write_yaml_file
from processforge_core.executions.composition import ExecutionStorage
from processforge_core.prepared import input as prepared_input
from processforge_core.runtime.drivers import RuntimeDriverDefinitionPolicy
from processforge_core.runtime.execution_admission import ExecutionAdmission

from .test_lifecycle import sql_cli_fixture as sql_cli_fixture
from .test_repository import isolated_path as isolated_path


@pytest.fixture
def legacy_manual(sql_cli_fixture: Any, monkeypatch: pytest.MonkeyPatch) -> Any:
    root, _repository, args, driver_path = sql_cli_fixture
    monkeypatch.setattr(
        core, "_execution_storage", lambda *_args, **_kwargs: ExecutionStorage("legacy")
    )
    monkeypatch.setattr(
        core, "_storage_first_write", lambda *_args, **_kwargs: (None, None)
    )
    driver = RuntimeDriverDefinitionPolicy().default_documents()["manual"]
    driver["id"] = "fixture-manual"
    write_yaml_file(driver_path, driver)
    assert core.command_worker_run_prepare(args) == 0
    paths = core._work_paths.worker_run(root, "run", "task")
    task = core._worker_assignment_service.load(root, "task")
    state = core.load_agent_run_state(root, "run", "task")
    document = prepared_input.load(root, task, state, core)
    assert "managed_scratch" not in document
    return root, args, paths, task, state


def test_public_prepare_reconciles_legacy_without_managed_scratch(
    legacy_manual: Any,
) -> None:
    root, args, paths, _task, state = legacy_manual
    state.update(status="running", pid=None)
    core._core_common_json_io.json_write(paths["status"], state)
    before_attempts = set((paths["root"] / "attempts").iterdir())
    assert core.command_worker_run_prepare(args) == 0
    current = core.load_agent_run_state(root, "run", "task")
    assert current["attempt"] == state["attempt"] and current["status"] == "running"
    assert current["failure_reason"] == "execution activity unknown"
    assert set((paths["root"] / "attempts").iterdir()) == before_attempts
    assert not ExecutionAdmission.held(root, None)
    assert not core._WORKER_LIFECYCLE_GATES.get()


def independent_admission(project: Path, workplace: Path) -> None:
    candidate = Path(__file__).resolve().parents[2]
    environment = dict(os.environ)
    environment["PYTHONPATH"] = os.pathsep.join(
        [str(candidate / "src"), str(candidate / "tools")]
    )
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            """
import sys,time
from pathlib import Path
from processforge_core.runtime.execution_admission import ExecutionAdmission
with ExecutionAdmission().start(Path(sys.argv[1]),Path(sys.argv[2]),deadline=time.monotonic()+0.5):
    print('admitted-during-collection-proof')
""",
            str(project),
            str(workplace),
        ],
        env=environment,
        cwd=candidate,
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert result.stdout.strip() == "admitted-during-collection-proof"


@pytest.mark.parametrize("drift", [False, True])
def test_real_collection_proof_releases_global_gate_and_revalidates_commit(
    legacy_manual: Any, monkeypatch: pytest.MonkeyPatch, drift: bool
) -> None:
    root, args, paths, task, state = legacy_manual
    workplace = root / "fixture-workplace"
    write_yaml_file(workplace / "workplace.yaml", {"id": "fixture-workplace"})
    write_yaml_file(
        root / ".pf/process-forge.local.yaml",
        {"workplace": {"manifest": (workplace / "workplace.yaml").as_posix()}},
    )
    report = root / ".pf/artifacts/report.md"
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text("verified report body\n" * 4096, encoding="utf-8")
    proof_started, release_proof = threading.Event(), threading.Event()
    results: list[int] = []
    failures: list[BaseException] = []
    captures: list[dict[str, Any]] = []
    output_checks: list[list[dict[str, Any]]] = []
    original_outputs = prepared_input.output_records
    original_commit = core._worker_phase_commit
    expected_new: dict[Path, bytes | None] = {}

    def delayed_output_proof(*proof_args: Any, **proof_kwargs: Any) -> Any:
        assert not ExecutionAdmission.held(root, workplace)
        proof_started.set()
        assert release_proof.wait(timeout=10), "test never released real output proof"
        records = original_outputs(*proof_args, **proof_kwargs)
        output_checks.append(records)
        return records

    @contextmanager
    def current_commit(*commit_args: Any, **commit_kwargs: Any) -> Iterator[None]:
        assert not core._WORKER_LIFECYCLE_GATES.get(), (
            "planning lock was not released before admission"
        )
        assert not ExecutionAdmission.held(root, workplace)
        if drift:
            with (
                core._worker_observation_admission(root),
                core.worker_run_lifecycle_lock(root, "run", "task"),
            ):
                core.write_agent_run_state(
                    root,
                    task,
                    {"id": "fixture-manual"},
                    "running",
                    attempt=2,
                    pid=os.getpid(),
                    command={"attempt": 2, "argv": ["new-worker"]},
                )
                expected_new.update(
                    {
                        paths[name]: core._observation_bytes(paths[name])
                        for name in ("status", "command", "exit", "process")
                    }
                )
        with original_commit(*commit_args, **commit_kwargs):
            yield

    def capture(envelope: dict[str, Any], *_args: Any) -> dict[str, Any]:
        captures.append(envelope)
        return {"accepted": True, "chat_message_ids": ["fixture-message"]}

    monkeypatch.setattr(prepared_input, "output_records", delayed_output_proof)
    monkeypatch.setattr(core, "_worker_phase_commit", current_commit)
    monkeypatch.setattr(host, "ingest_event", capture)

    def collect() -> None:
        try:
            results.append(core.command_worker_run_collect(args))
        except BaseException as error:
            failures.append(error)

    collector = threading.Thread(target=collect)
    collector.start()
    try:
        assert proof_started.wait(timeout=10), failures
        independent_admission(root, workplace)
    finally:
        release_proof.set()
        collector.join(timeout=15)
    assert not collector.is_alive() and not failures, failures
    assert output_checks, "the real collection output hashing did not run"
    assert output_checks[0][0]["checksum"] == prepared_input.digest(report.read_bytes())
    completion = root / state["prepared_input"]["path"]
    completion = completion.with_name("collection-complete.json")
    if drift:
        assert results == [1] and not captures
        assert not completion.exists()
        assert {
            path: core._observation_bytes(path) for path in expected_new
        } == expected_new
        current = core.load_agent_run_state(root, "run", "task")
        assert current["attempt"] == 2 and current["status"] == "running"
    else:
        assert results == [0] and len(captures) == 1
        assert captures[0]["raw_payload"]["report_content"] == report.read_text(
            encoding="utf-8"
        )
        assert json.loads(completion.read_text(encoding="utf-8"))["receipt_id"]


@pytest.mark.parametrize("stopping", [False, True])
def test_actual_start_waits_for_heavy_planner_without_holding_workplace_gate(
    legacy_manual: Any, monkeypatch: pytest.MonkeyPatch, stopping: bool
) -> None:
    root, args, _paths, task, state = legacy_manual
    workplace = root / "fixture-workplace"
    write_yaml_file(workplace / "workplace.yaml", {"id": "fixture-workplace"})
    write_yaml_file(
        root / ".pf/process-forge.local.yaml",
        {"workplace": {"manifest": (workplace / "workplace.yaml").as_posix()}},
    )
    report = root / ".pf/artifacts/report.md"
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text("real planner proof\n" * 4096, encoding="utf-8")
    proof_started, release_proof, start_try = (
        threading.Event(),
        threading.Event(),
        threading.Event(),
    )
    original_outputs = prepared_input.output_records
    original_lock = core.worker_run_lifecycle_lock
    original_register = host.register_worker_project
    registered: list[Path] = []
    failures: list[BaseException] = []
    start_results: list[int] = []

    def output_proof(*proof_args: Any, **proof_kwargs: Any) -> Any:
        proof_started.set()
        assert release_proof.wait(timeout=10)
        return original_outputs(*proof_args, **proof_kwargs)

    @contextmanager
    def lifecycle(*lock_args: Any, **lock_kwargs: Any) -> Iterator[Any]:
        if lock_kwargs.get("timeout_seconds") == 0.0:
            start_try.set()
        with original_lock(*lock_args, **lock_kwargs) as held:
            yield held

    def register(
        selected_workplace: Path, selected_project: Path, selected_core: Any
    ) -> None:
        registered.append(selected_project)
        original_register(selected_workplace, selected_project, selected_core)

    monkeypatch.setattr(prepared_input, "output_records", output_proof)
    monkeypatch.setattr(core, "worker_run_lifecycle_lock", lifecycle)
    monkeypatch.setattr(host, "register_worker_project", register)

    def planner() -> None:
        try:
            with core._worker_planning_phase(root, "run", "task"):
                prepared_input.collection_receipt(root, task, state, core)
        except BaseException as error:
            failures.append(error)

    def start() -> None:
        try:
            start_results.append(core.command_worker_run_start(args))
        except BaseException as error:
            failures.append(error)

    planning_thread, start_thread = (
        threading.Thread(target=planner),
        threading.Thread(target=start),
    )
    planning_thread.start()
    try:
        assert proof_started.wait(timeout=10), failures
        start_thread.start()
        assert start_try.wait(timeout=10), failures
        independent_admission(root, workplace)
        assert not registered, "start registered before acquiring its task lock"
        if stopping:
            service = workplace / "runtime/pf-runtime/service.json"
            service.parent.mkdir(parents=True, exist_ok=True)
            service.write_text('{"status":"stopping"}', encoding="utf-8")
    finally:
        release_proof.set()
        planning_thread.join(timeout=15)
        if start_thread.ident is not None:
            start_thread.join(timeout=15)
    assert not planning_thread.is_alive() and not start_thread.is_alive()
    assert not failures, failures
    assert start_results == ([1] if stopping else [0])
    assert len(registered) == (0 if stopping else 1)
