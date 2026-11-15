"""SQL startup and explicit legacy recovery keep long reads outside admission."""

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
from processforge_core.executions.model import ExecutionError
from processforge_core.prepared import input as prepared_input
from processforge_core.runtime.drivers import RuntimeDriverDefinitionPolicy
from processforge_core.runtime.execution_admission import ExecutionAdmission

from .test_lifecycle import _forbid_legacy_effects
from .test_lifecycle import sql_cli_fixture as sql_cli_fixture
from .test_repository import isolated_path as isolated_path


@pytest.fixture
def legacy_manual(sql_cli_fixture: Any, monkeypatch: pytest.MonkeyPatch) -> Any:
    root, _repository, args, driver_path = sql_cli_fixture
    monkeypatch.setattr(
        core, "_execution_storage", lambda *_args, **_kwargs: ExecutionStorage("legacy")
    )
    driver = RuntimeDriverDefinitionPolicy().default_documents()["manual"]
    driver["id"] = "fixture-manual"
    write_yaml_file(driver_path, driver)
    # Seed a historical attempt through the private compatibility mechanism.
    # Ordinary public prepare/start must require migration first.
    core.prepare_worker_run(root, "task", args.driver)
    paths = core._work_paths.worker_run(root, "run", "task")
    task = core._worker_assignment_service.load(root, "task")
    state = core.load_agent_run_state(root, "run", "task")
    document = prepared_input.load(root, task, state, core)
    assert "managed_scratch" not in document
    return root, args, paths, task, state


def test_legacy_recovery_reconciles_unknown_tree_without_managed_scratch(
    legacy_manual: Any,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root, args, paths, _task, state = legacy_manual
    state.update(status="running", pid=None)
    core._core_common_json_io.json_write(paths["status"], state)
    before_attempts = set((paths["root"] / "attempts").iterdir())
    before_task = core._worker_assignment_service.load(root, "task")
    _forbid_legacy_effects(monkeypatch)
    with pytest.raises(ExecutionError, match="^execution_activity_unknown$"):
        core.existing_running_worker_run(root, before_task, args.driver)
    assert core._worker_assignment_service.load(root, "task") == before_task
    current = core.load_agent_run_state(root, "run", "task")
    assert current["attempt"] == state["attempt"] and current["status"] == "running"
    assert current["pid"] is None
    assert current["failure_reason"] == "execution activity unknown"
    assert set((paths["root"] / "attempts").iterdir()) == before_attempts
    assert not ExecutionAdmission.held(root, None)
    assert not core._WORKER_LIFECYCLE_GATES.get()
    independent_admission(root, root)


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


@pytest.fixture
def sql_manual(sql_cli_fixture: Any) -> Any:
    root, _repository, args, driver_path = sql_cli_fixture
    driver = RuntimeDriverDefinitionPolicy().default_documents()["manual"]
    driver["id"] = "fixture-manual"
    write_yaml_file(driver_path, driver)
    assert core.command_worker_run_prepare(args) == 0
    paths = core._work_paths.worker_run(root, "run", "task")
    task = core._worker_assignment_service.load(root, "task")
    state = core.load_agent_run_state(root, "run", "task")
    return root, args, paths, task, state


@pytest.mark.parametrize("stopping", [False, True])
def test_actual_start_waits_for_heavy_planner_without_holding_workplace_gate(
    sql_manual: Any, monkeypatch: pytest.MonkeyPatch, stopping: bool
) -> None:
    root, args, _paths, task, state = sql_manual
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


@pytest.mark.parametrize("pending_retry", [False, True])
def test_native_start_rebuilds_proof_after_admission_contention(
    legacy_manual: Any, monkeypatch: pytest.MonkeyPatch, pending_retry: bool
) -> None:
    """A competing process publishes a retry; stale proof never reserves."""
    import time
    from contextlib import ExitStack
    from types import SimpleNamespace

    from processforge_core.executions.model import ExecutionError
    from processforge_core.prepared import resources
    from processforge_core.prepared.retry_publication import APPLIED

    root, _args, _paths, original_task, state = legacy_manual
    workplace = root / "fixture-workplace"
    write_yaml_file(workplace / "workplace.yaml", {"id": "fixture-workplace"})
    write_yaml_file(
        root / ".pf/process-forge.local.yaml",
        {"workplace": {"manifest": (workplace / "workplace.yaml").as_posix()}},
    )
    task = dict(original_task, parameters={"native_maintenance_job": {"fixture": True}})
    ready, proceed = root / "competitor-ready", root / "competitor-proceed"
    opened: list[int] = []
    closed: list[int] = []
    admitted: list[int] = []
    refused: list[str] = []

    @contextmanager
    def held_material(*_args: Any, **_kwargs: Any) -> Iterator[Any]:
        # Only material validation is a seam. Task/admission locks are real OS
        # locks in separate processes; cold_handoff covers actual Windows inputs.
        assert not ExecutionAdmission.held(root, workplace)
        number = len(opened)
        opened.append(number)
        try:
            yield SimpleNamespace(task=task, number=number)
        finally:
            closed.append(number)
            proceed.touch()

    monkeypatch.setattr(resources, "native_start_preflight", held_material)
    candidate = Path(__file__).resolve().parents[2]
    environment = dict(os.environ)
    environment["PYTHONPATH"] = os.pathsep.join(
        [str(candidate / "src"), str(candidate / "tools")]
    )
    competitor = subprocess.Popen(
        [
            sys.executable,
            "-B",
            "-c",
            """
import sys,time
from pathlib import Path
import processforge as core
root,ready,proceed,receipt=map(Path,sys.argv[1:5])
with core._worker_start_admission(root,_defer_registration=True):
    ready.touch()
    deadline=time.monotonic()+10
    while not proceed.exists():
        if time.monotonic()>=deadline:
            raise RuntimeError("starter kept its task proof while waiting on admission")
        time.sleep(0.01)
    with core.worker_run_lifecycle_lock(root,"run","task",timeout_seconds=5):
        if sys.argv[5]=="pending":
            receipt.unlink()
        print("competing-task-published",flush=True)
""",
            str(root),
            str(ready),
            str(proceed),
            str((root / state["prepared_input"]["path"]).with_name(APPLIED)),
            "pending" if pending_retry else "unchanged",
        ],
        cwd=candidate,
        env=environment,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        deadline = time.monotonic() + 10
        while not ready.exists():
            assert competitor.poll() is None, "competitor failed before admission"
            assert time.monotonic() < deadline, "competitor did not acquire admission"
            time.sleep(0.01)
        try:
            with ExitStack() as material:
                with core._legacy_start_admission(root, task, None, material) as proof:
                    assert ExecutionAdmission.held(root, workplace)
                    admitted.append(proof.number)
                assert not ExecutionAdmission.held(root, workplace)
                assert not core._WORKER_LIFECYCLE_GATES.get()
                assert proof.number not in closed, "consumer material released early"
        except ExecutionError as error:
            refused.append(error.code)
    finally:
        proceed.touch()
        try:
            stdout, stderr = competitor.communicate(timeout=15)
        except subprocess.TimeoutExpired:
            competitor.kill()
            stdout, stderr = competitor.communicate(timeout=5)
            pytest.fail("competing process did not release its gates: " + stderr)
    assert competitor.returncode == 0, stdout + stderr
    assert stdout.strip() == "competing-task-published"
    assert sorted(opened) == sorted(closed), "failed or consumed material leaked"
    if pending_retry:
        assert refused == ["execution_activity_unknown"] and not admitted
    else:
        assert not refused and len(admitted) == 1 and len(opened) >= 2
        assert admitted[0] > 0, "proof from before contention was reused"
    independent_admission(root, workplace)


def test_native_start_does_not_replay_unknown_body_outcome(
    legacy_manual: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    from contextlib import ExitStack
    from types import SimpleNamespace

    from processforge_core.executions.model import ExecutionError
    from processforge_core.prepared import resources

    root, _args, _paths, original_task, _state = legacy_manual
    task = dict(original_task, parameters={"native_maintenance_job": {"fixture": True}})
    captures: list[str] = []

    @contextmanager
    def held_material(*_args: Any, **_kwargs: Any) -> Iterator[Any]:
        captures.append("open")
        try:
            yield SimpleNamespace(task=task)
        finally:
            captures.append("close")

    monkeypatch.setattr(resources, "native_start_preflight", held_material)
    failure = ExecutionError("execution_activity_unknown")
    failure.__dict__["admission_reason"] = "contention_timeout"
    with pytest.raises(ExecutionError) as result, ExitStack() as material:
        with core._legacy_start_admission(root, task, None, material):
            raise failure
    assert result.value is failure
    assert captures == ["open", "close"]
    assert not ExecutionAdmission.held(root, None)
    assert not core._WORKER_LIFECYCLE_GATES.get()


def test_native_retry_proof_cannot_escape_its_exact_live_locks(
    legacy_manual: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    from contextlib import ExitStack
    from contextvars import copy_context
    from types import SimpleNamespace

    from processforge_core.prepared import resources

    root, _args, _paths, original_task, _state = legacy_manual
    task = dict(original_task, parameters={"native_maintenance_job": {"fixture": True}})
    discoveries: list[str] = []
    original_discover = core._retry_refuse_pending

    def discover(*args: Any) -> None:
        discoveries.append("checked")
        original_discover(*args)

    @contextmanager
    def held_material(*_args: Any, **_kwargs: Any) -> Iterator[Any]:
        yield SimpleNamespace(task=task)

    monkeypatch.setattr(resources, "native_start_preflight", held_material)
    monkeypatch.setattr(core, "_retry_refuse_pending", discover)
    with ExitStack() as material:
        with core._legacy_start_admission(root, task, None, material):
            before = len(discoveries)
            core._commit_legacy_observation(root, task)
            assert len(discoveries) == before, "held retry proof was rescanned"
            assert core._legacy_start_retry_proven(root, task)
            assert not core._legacy_start_retry_proven(
                root, dict(task, id="another-task")
            )
            assert not core._legacy_start_retry_proven(root.parent, task)
            copied = copy_context()
            observed: list[bool] = []
            worker = threading.Thread(
                target=lambda: observed.append(
                    copied.run(core._legacy_start_retry_proven, root, task)
                )
            )
            worker.start()
            worker.join(timeout=5)
            assert not worker.is_alive() and observed == [False]
            if hasattr(os, "fork"):
                child = os.fork()
                if child == 0:
                    os._exit(1 if core._legacy_start_retry_proven(root, task) else 0)
                _, status = os.waitpid(child, 0)
                assert os.waitstatus_to_exitcode(status) == 0
        assert not copied.run(core._legacy_start_retry_proven, root, task)
        with core._worker_commit_locks(root, "run", "task", start=True):
            before = len(discoveries)
            copied.run(core._commit_legacy_observation, root, task)
            assert len(discoveries) == before + 1
            assert not copied.run(core._legacy_start_retry_proven, root, task)


def test_native_start_task_contention_returns_normalized_refusal(
    legacy_manual: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A real competing task owner must not leak a lock path through SystemExit."""
    import time
    from contextlib import ExitStack

    from processforge_core.executions.model import ExecutionError
    from processforge_core.prepared import resources

    root, _args, _paths, original_task, _state = legacy_manual
    task = dict(original_task, parameters={"native_maintenance_job": {"fixture": True}})
    ready, proceed = root / "task-owner-ready", root / "task-owner-proceed"
    original_lock = core.worker_run_lifecycle_lock
    budgets: list[float] = []

    @contextmanager
    def bounded_lock(*args: Any, **kwargs: Any) -> Iterator[Any]:
        budgets.append(kwargs["timeout_seconds"])
        kwargs["timeout_seconds"] = min(kwargs["timeout_seconds"], 0.05)
        with original_lock(*args, **kwargs) as lease:
            yield lease

    @contextmanager
    def forbidden_material(*_args: Any, **_kwargs: Any) -> Iterator[Any]:
        pytest.fail("material validation started before obtaining the task lock")
        yield

    monkeypatch.setattr(core, "worker_run_lifecycle_lock", bounded_lock)
    monkeypatch.setattr(resources, "native_start_preflight", forbidden_material)
    candidate = Path(__file__).resolve().parents[2]
    environment = dict(os.environ)
    environment["PYTHONPATH"] = os.pathsep.join(
        [str(candidate / "src"), str(candidate / "tools")]
    )
    owner = subprocess.Popen(
        [
            sys.executable,
            "-B",
            "-c",
            """
import sys,time
from pathlib import Path
import processforge as core
root,ready,proceed=map(Path,sys.argv[1:])
with core.worker_run_lifecycle_lock(root,"run","task"):
    ready.touch()
    deadline=time.monotonic()+10
    while not proceed.exists():
        if time.monotonic()>=deadline:
            raise RuntimeError("test did not release task owner")
        time.sleep(0.01)
    print("task-owner-released",flush=True)
""",
            str(root),
            str(ready),
            str(proceed),
        ],
        cwd=candidate,
        env=environment,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        deadline = time.monotonic() + 10
        while not ready.exists():
            assert owner.poll() is None, "task owner exited before acquisition"
            assert time.monotonic() < deadline, "task owner did not acquire its lock"
            time.sleep(0.01)
        with pytest.raises(ExecutionError) as refusal, ExitStack() as material:
            with core._legacy_start_admission(root, task, None, material):
                pytest.fail("a competing owner was ignored")
        assert str(refusal.value) == "execution_activity_unknown"
        assert budgets and 0 < budgets[0] <= 30.0
        assert not ExecutionAdmission.held(root, None)
        assert not core._WORKER_LIFECYCLE_GATES.get()
    finally:
        proceed.touch()
        try:
            stdout, stderr = owner.communicate(timeout=15)
        except subprocess.TimeoutExpired:
            owner.kill()
            stdout, stderr = owner.communicate(timeout=5)
            pytest.fail("task owner did not exit: " + stderr)
    assert owner.returncode == 0, stdout + stderr
    assert stdout.strip() == "task-owner-released"


def test_native_start_preserves_unclassified_task_lock_exit(
    legacy_manual: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    from contextlib import ExitStack

    root, _args, _paths, original_task, _state = legacy_manual
    task = dict(original_task, parameters={"native_maintenance_job": {"fixture": True}})
    failure = SystemExit("unclassified owner failure")

    @contextmanager
    def refused_lock(*_args: Any, **_kwargs: Any) -> Iterator[Any]:
        raise failure
        yield

    monkeypatch.setattr(core, "worker_run_lifecycle_lock", refused_lock)
    with pytest.raises(SystemExit) as refusal, ExitStack() as material:
        with core._legacy_start_admission(root, task, None, material):
            pytest.fail("unclassified lock failure was ignored")
    assert refusal.value is failure
