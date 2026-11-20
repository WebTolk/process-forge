"""Slow observations release admission; commits still honor stopping/currentness."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import threading
from collections.abc import Iterator
from contextlib import contextmanager, nullcontext
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pf_native_control
import processforge as core
import pytest
from pf_runtime import host

from processforge_core.executions.model import ExecutionError
from processforge_core.project import configuration_inputs
from processforge_core.runtime.execution_admission import ExecutionAdmission

_ROUTE_PROJECT = host.route_project


@pytest.fixture
def runtime_context(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Any:
    project, workplace = tmp_path / "project", tmp_path / "workplace"
    (project / ".pf").mkdir(parents=True)
    workplace.mkdir()
    (project / ".pf/process-forge.yaml").write_text(
        "project:\n  id: fixture-project\n", encoding="utf-8"
    )
    events: list[str] = []

    @contextmanager
    def native_operation() -> Iterator[None]:
        events.append("native_enter")
        try:
            yield
        finally:
            events.append("native_leave")

    monkeypatch.setattr(
        pf_native_control,
        "current_entry",
        lambda: SimpleNamespace(operation=native_operation),
    )
    monkeypatch.setattr(
        configuration_inputs, "configuration_operation", lambda *_: nullcontext()
    )

    def route(*_args: object) -> dict[str, Any]:
        assert ExecutionAdmission.held(project, workplace)
        events.append("route")
        return {
            "project_id": "fixture-project",
            "project_root": str(project),
            "effective_mode": "organized",
            "revision": events.count("route"),
        }

    def commit(name: str) -> None:
        assert ExecutionAdmission.held(project, workplace)
        events.append(name)

    def flush(*_args: object) -> None:
        assert not ExecutionAdmission.held(project, workplace)
        assert "native_leave" not in events
        events.append("flush")

    core = SimpleNamespace(
        update_stale_agent_presence=lambda *_: None,
        command_agent_director_tick=lambda *_: 0,
        supervisor_tick_result=lambda *_: {"failed": []},
        flush_pending_event_dispatches=flush,
        rel=lambda path, _root: str(path),
    )
    monkeypatch.setattr(host, "route_project", route)
    monkeypatch.setattr(host, "load_state", lambda *_: {"projects": []})
    monkeypatch.setattr(host, "save_state", lambda *_: commit("save"))
    monkeypatch.setattr(host, "refresh_stage_obligations", lambda *_: project / "ui.md")
    return project, workplace, core, events


def independent_admission(project: Path, workplace: Path) -> None:
    source = Path(__file__).resolve().parents[2]
    environment = dict(os.environ)
    environment["PYTHONPATH"] = os.pathsep.join(
        [str(source / "src"), str(source / "tools")]
    )
    probe = subprocess.run(
        [
            sys.executable,
            "-c",
            """
import sys,time
from pathlib import Path
from processforge_core.runtime.execution_admission import ExecutionAdmission
with ExecutionAdmission().start(Path(sys.argv[1]),Path(sys.argv[2]),deadline=time.monotonic()+0.5):
    print('independent-admission')
""",
            str(project),
            str(workplace),
        ],
        env=environment,
        cwd=source,
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert probe.returncode == 0, probe.stdout + probe.stderr
    assert probe.stdout.strip() == "independent-admission"


@pytest.mark.parametrize("slow_phase", ["inspector", "projection", "flush"])
def test_slow_observation_does_not_block_independent_admission(
    runtime_context: Any, monkeypatch: pytest.MonkeyPatch, slow_phase: str
) -> None:
    project, workplace, core, events = runtime_context

    def slow_callback(*args: object) -> Any:
        assert events[0] == "native_enter" and "native_leave" not in events
        assert not ExecutionAdmission.held(project, workplace)
        if slow_phase == "inspector":
            assert getattr(args[0], "start_allowed") is False
        independent_admission(project, workplace)
        events.append(slow_phase)
        return {"failed": []} if slow_phase == "inspector" else project / "ui.md"

    if slow_phase == "inspector":
        core.supervisor_tick_result = slow_callback
    elif slow_phase == "flush":
        core.flush_pending_event_dispatches = slow_callback
    else:
        monkeypatch.setattr(host, "refresh_stage_obligations", slow_callback)
    payload, status = host.tick_payload(workplace, [project], core, inspector=True)
    assert status == 0 and payload["scheduler_status"] == "ok"
    assert events[-1] == "native_leave"
    assert events.index("flush") < events.index("save")
    assert events.count("route") == 3  # initial snapshot, flush, fresh publication


@pytest.mark.parametrize("stop_phase", ["initial", "flush", "publication"])
def test_stopping_prevents_later_tick_commits(
    runtime_context: Any, monkeypatch: pytest.MonkeyPatch, stop_phase: str
) -> None:
    project, workplace, core, events = runtime_context

    def stop() -> None:
        path = workplace / "runtime/pf-runtime/service.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text('{"status":"stopping"}', encoding="utf-8")

    if stop_phase == "initial":
        stop()
    elif stop_phase == "flush":

        def stop_before_flush(*_args: object) -> dict[str, Any]:
            stop()
            return {"failed": []}

        core.supervisor_tick_result = stop_before_flush
    else:

        def stop_before_publication(*_args: object) -> Path:
            stop()
            return project / "ui.md"

        monkeypatch.setattr(host, "refresh_stage_obligations", stop_before_publication)
    with pytest.raises(ExecutionError, match="execution_activity_unknown"):
        host.tick_payload(workplace, [project], core, inspector=True)
    assert "save" not in events
    assert ("flush" in events) is (stop_phase == "publication")
    assert events[-1] == "native_leave"


@pytest.mark.parametrize("change", ["disappeared", "revived", "changed", "unchanged"])
def test_presence_expiration_revalidates_actor_before_commit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, change: str
) -> None:
    workplace = tmp_path / "workplace"
    presence = {
        "agent_id": "actor",
        "session_id": "session",
        "status": "online",
        "last_seen_at": "2020-01-01T00:00:00Z",
        "heartbeat_ttl_seconds": 10,
    }
    path = core.agent_presence_path(workplace, "actor", "session")
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps(presence), encoding="utf-8")
    monkeypatch.setattr(core, "iter_agent_presence", lambda *_: [dict(presence)])
    ledger: list[dict[str, Any]] = []
    monkeypatch.setattr(
        type(core._agent_workplace_registry),
        "append_agent_ledger_event",
        lambda _registry, _root, event: ledger.append(event),
    )

    @contextmanager
    def commit(*_args: object) -> Iterator[None]:
        if change == "disappeared":
            path.unlink()
        elif change in {"revived", "changed"}:
            current = dict(presence)
            current["last_seen_at" if change == "revived" else "status"] = (
                "2999-01-01T00:00:00Z" if change == "revived" else "checked_out"
            )
            path.write_text(json.dumps(current), encoding="utf-8")
        yield

    monkeypatch.setattr(core, "_director_commit", commit)
    core.update_stale_agent_presence(workplace)
    assert len(ledger) == (1 if change == "unchanged" else 0)
    if path.exists():
        status = json.loads(path.read_text(encoding="utf-8"))["status"]
        assert status == (
            "stale"
            if change == "unchanged"
            else "checked_out"
            if change == "changed"
            else "online"
        )


def test_director_commit_honors_stopping_before_mutation(
    tmp_path: Path,
) -> None:
    workplace = tmp_path / "workplace"
    service = workplace / "runtime/pf-runtime/service.json"
    service.parent.mkdir(parents=True)
    service.write_text('{"status":"stopping"}', encoding="utf-8")
    with pytest.raises(ExecutionError, match="execution_activity_unknown"):
        with core._director_commit(None, workplace):
            pytest.fail("Director mutation crossed a stopping fence")


@pytest.mark.parametrize("change", ["unchanged", "handoff", "presence", "stopping"])
@pytest.mark.parametrize("session_id", ["session", ""])
def test_director_scans_without_admission_and_revalidates_selected_commit(
    runtime_context: Any, monkeypatch: pytest.MonkeyPatch, change: str, session_id: str
) -> None:
    project, workplace, _stub, _events = runtime_context
    handoff_path = project / ".pf/handoffs/handoff/handoff.yaml"
    handoff = {"id": "handoff", "status": "waiting_for_agent", "to": {}}
    core._core_common_yaml_io.write_yaml_file(handoff_path, handoff)
    presence = {
        "agent_id": "actor",
        "session_id": session_id,
        "status": "online",
        "last_seen_at": "2999-01-01T00:00:00Z",
    }
    presence_path = core.agent_presence_path(workplace, "actor", session_id)
    presence_path.parent.mkdir(parents=True)
    presence_path.write_text(json.dumps(presence), encoding="utf-8")
    monkeypatch.setattr(
        core, "resolve_workplace_root", lambda *_args, **_kwargs: workplace
    )
    monkeypatch.setattr(core, "mark_expired_agent_leases", lambda *_args, **_kwargs: 0)
    grants: list[str] = []
    grant_command = core.command_agent_lease_grant

    def broad_lookup(*_args: object) -> dict[str, Any]:
        pytest.fail("Director reintroduced an unbounded presence lookup during commit")

    monkeypatch.setattr(core, "read_agent_presence", broad_lookup)

    def scan(*_args: object, **_kwargs: object) -> list[dict[str, Any]]:
        assert not ExecutionAdmission.held(project, workplace)
        independent_admission(project, workplace)
        if change == "handoff":
            core._core_common_yaml_io.write_yaml_file(
                handoff_path, {**handoff, "status": "accepted"}
            )
        elif change == "presence":
            presence_path.write_text(
                json.dumps({**presence, "status": "checked_out"}), encoding="utf-8"
            )
        elif change == "stopping":
            service = workplace / "runtime/pf-runtime/service.json"
            service.parent.mkdir(parents=True, exist_ok=True)
            service.write_text('{"status":"stopping"}', encoding="utf-8")
        return [presence]

    def grant(args: argparse.Namespace) -> int:
        assert ExecutionAdmission.held(project, workplace)
        grants.append(args.id)
        return grant_command(args)

    monkeypatch.setattr(core, "checked_in_agents", scan)
    monkeypatch.setattr(core, "command_agent_lease_grant", grant)
    args = argparse.Namespace(
        project_root=str(project),
        workplace=str(workplace),
        project_id="fixture-project",
        wait_ttl=3600,
        lease_ttl=3600,
    )
    if change == "stopping":
        with pytest.raises(ExecutionError, match="execution_activity_unknown"):
            core.command_agent_director_tick(args)
    else:
        assert core.command_agent_director_tick(args) == 0
    assert bool(grants) is (change == "unchanged")
    if grants:
        assert core.load_lease(workplace, grants[0])["session_id"] == session_id
    current = core.load_yaml_document(handoff_path)
    assert current["status"] == (
        "ready"
        if change == "unchanged"
        else "accepted"
        if change == "handoff"
        else "waiting_for_agent"
    )


def test_expired_lease_renewal_is_not_overwritten(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    workplace, project = tmp_path / "workplace", tmp_path / "project"
    path = (
        core._agent_workplace_registry.workplace_agent_leases_dir(workplace)
        / "lease.yaml"
    )
    lease = {"id": "lease", "status": "active", "expires_at": "2020-01-01T00:00:00Z"}
    core._core_common_yaml_io.write_yaml_file(path, lease)
    renewed = {**lease, "expires_at": "2999-01-01T00:00:00Z"}

    @contextmanager
    def commit(*_args: object) -> Iterator[None]:
        core._core_common_yaml_io.write_yaml_file(path, renewed)
        yield

    monkeypatch.setattr(core, "_director_commit", commit)
    assert core.mark_expired_agent_leases(workplace, project_root=project) == 0
    assert core.load_yaml_document(path) == renewed


@pytest.mark.parametrize("automatic", [False, True])
def test_director_rechecks_live_project_mode_after_selection(
    runtime_context: Any, monkeypatch: pytest.MonkeyPatch, automatic: bool
) -> None:
    project, workplace, _stub, _events = runtime_context
    manifest = project / ".pf/process-forge.yaml"
    document = {
        "project": {"id": "fixture-project"},
        "coordination": {"mode": "organized"},
    }
    core._core_common_yaml_io.write_yaml_file(manifest, document)
    core._core_common_yaml_io.write_yaml_file(
        workplace / "workplace.yaml",
        {"id": "fixture-workplace", "coordination": {"director_enabled": True}},
    )
    handoff_path = project / ".pf/handoffs/handoff/handoff.yaml"
    handoff = {"id": "handoff", "status": "waiting_for_agent", "to": {}}
    core._core_common_yaml_io.write_yaml_file(handoff_path, handoff)
    before = handoff_path.read_bytes()
    presence = {
        "agent_id": "actor",
        "session_id": "session",
        "status": "online",
        "last_seen_at": "2999-01-01T00:00:00Z",
    }
    core.write_agent_presence(workplace, presence)
    monkeypatch.setattr(host, "route_project", _ROUTE_PROJECT)
    monkeypatch.setattr(
        core, "resolve_workplace_root", lambda *_args, **_kwargs: workplace
    )
    monkeypatch.setattr(core, "mark_expired_agent_leases", lambda *_args, **_kwargs: 0)
    monkeypatch.setattr(core, "flush_pending_event_dispatches", lambda *_: None)

    def scan(*_args: object, **_kwargs: object) -> list[dict[str, Any]]:
        assert not ExecutionAdmission.held(project, workplace)
        core._core_common_yaml_io.write_yaml_file(
            manifest, {**document, "coordination": {"mode": "simple"}}
        )
        return [presence]

    monkeypatch.setattr(core, "checked_in_agents", scan)
    if automatic:
        _payload, status = host.tick_payload(workplace, [project], core, director=True)
        assert status == 0
        assert handoff_path.read_bytes() == before
        assert not list(
            core._agent_workplace_registry.workplace_agent_leases_dir(workplace).glob(
                "*.yaml"
            )
        )
    else:
        args = argparse.Namespace(
            project_root=str(project),
            workplace=str(workplace),
            project_id="fixture-project",
            wait_ttl=3600,
            lease_ttl=3600,
        )
        assert core.command_agent_director_tick(args) == 0
        assert core.load_yaml_document(handoff_path)["status"] == "ready"


@pytest.fixture
def legacy_observation(runtime_context: Any, monkeypatch: pytest.MonkeyPatch) -> Any:
    project, workplace, _stub, _events = runtime_context
    monkeypatch.setattr(
        core,
        "_execution_storage",
        lambda *_args, **_kwargs: SimpleNamespace(repository=None),
    )
    task = {"id": "worker", "run_id": "run"}
    driver = {"id": "shell"}
    paths = core._work_paths.worker_run(project, "run", "worker")
    paths["root"].mkdir(parents=True)
    core._core_common_yaml_io.write_yaml_file(
        core._work_paths.assignment_document(project, "worker"), task
    )
    state = core.write_agent_run_state(
        project,
        task,
        driver,
        "running",
        attempt=1,
        pid=123,
        started_at="2026-11-02T00:00:00Z",
        command={"attempt": 1, "argv": ["old"]},
    )
    core._core_common_json_io.json_write(paths["process"], {"attempt": 1, "pid": 123})
    core._core_common_json_io.json_write(
        paths["exit"],
        {"exit_code": 0, "status": "completed", "finished_at": "2026-11-02T00:00:01Z"},
    )
    emitted: list[str] = []
    monkeypatch.setattr(
        core,
        "_process_event_recorder",
        SimpleNamespace(
            emit_process_event=lambda _root, event, **_kwargs: emitted.append(event)
        ),
    )
    return project, workplace, task, driver, paths, state, emitted


def test_delayed_legacy_observation_preserves_new_live_attempt(
    legacy_observation: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    project, _workplace, task, driver, paths, state, emitted = legacy_observation
    key = core._core_runtime_observation_inputs.worker_process_key(
        project, "run", "worker"
    )
    retained = core._core_runtime_observation_inputs.DETACHED_WORKER_PROCESSES
    live = subprocess.Popen(
        [sys.executable, "-c", "import sys;sys.stdin.buffer.read(1)"],
        stdin=subprocess.PIPE,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
    )
    expected: dict[Path, bytes | None] = {}
    failures: list[BaseException] = []

    def next_attempt() -> None:
        try:
            with (
                core._worker_observation_admission(project),
                core.worker_run_lifecycle_lock(project, "run", "worker"),
            ):
                core.write_agent_run_state(
                    project,
                    task,
                    driver,
                    "running",
                    attempt=2,
                    pid=live.pid,
                    started_at="2026-11-02T00:01:00Z",
                    command={"attempt": 2, "argv": ["new"]},
                )
                core._core_common_json_io.json_write(
                    paths["process"], {"attempt": 2, "pid": live.pid}
                )
                paths["exit"].unlink()
                retained[key] = live
                expected.update(
                    {
                        paths[name]: core._observation_bytes(paths[name])
                        for name in ("status", "command", "process", "exit")
                    }
                )
        except BaseException as error:
            failures.append(error)

    def delayed_probe(*_args: object, **_kwargs: object) -> bool:
        assert not ExecutionAdmission.held(project, None)
        writer = threading.Thread(target=next_attempt)
        writer.start()
        writer.join(timeout=5)
        assert not writer.is_alive(), "retry could not commit while old observer probed"
        assert not failures, failures
        return True

    monkeypatch.setattr(core, "_legacy_tree_probe", delayed_probe)
    try:
        current = core.observe_worker_run(project, task, driver, state)
        assert current["attempt"] == 2 and current["pid"] == live.pid
        assert current["status"] == "running"
        assert {path: core._observation_bytes(path) for path in expected} == expected
        assert retained[key] is live and live.poll() is None
        assert not emitted
        assert core._LEGACY_OBSERVATION.get() is None
    finally:
        retained.pop(key, None)
        try:
            live.communicate(input=b"x", timeout=5)
        except subprocess.TimeoutExpired:
            live.kill()
            live.communicate(timeout=5)


def test_legacy_observation_reuses_admitted_lifecycle_without_deadlock(
    legacy_observation: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    project, _workplace, task, driver, _paths, state, _emitted = legacy_observation
    monkeypatch.setattr(core, "_legacy_tree_probe", lambda *_args, **_kwargs: True)

    def observed() -> None:
        assert ExecutionAdmission.held(project, None)
        with core.worker_run_lifecycle_lock(project, "run", "worker"):
            current = core.observe_worker_run(project, task, driver, state)
        assert current["attempt"] == 1 and current["status"] == "completed"

    with (
        core._worker_start_admission(project),
        core.worker_run_lifecycle_lock(project, "run", "worker"),
    ):
        observed()
    assert not core._WORKER_LIFECYCLE_GATES.get()
    assert not ExecutionAdmission.held(project, None)


def test_legacy_observation_checks_stopping_before_any_commit(
    legacy_observation: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    project, workplace, task, driver, paths, state, emitted = legacy_observation
    core._core_common_yaml_io.write_yaml_file(
        workplace / "workplace.yaml", {"id": "fixture-workplace"}
    )
    core._core_common_yaml_io.write_yaml_file(
        project / ".pf/process-forge.local.yaml",
        {"workplace": {"manifest": (workplace / "workplace.yaml").as_posix()}},
    )
    before = {
        paths[name]: core._observation_bytes(paths[name])
        for name in ("status", "command", "exit", "process")
    }

    def stop_during_probe(*_args: object, **_kwargs: object) -> bool:
        service = workplace / "runtime/pf-runtime/service.json"
        service.parent.mkdir(parents=True, exist_ok=True)
        service.write_text('{"status":"stopping"}', encoding="utf-8")
        return True

    monkeypatch.setattr(core, "_legacy_tree_probe", stop_during_probe)
    with pytest.raises(ExecutionError, match="execution_activity_unknown"):
        core.observe_worker_run(project, task, driver, state)
    assert {path: core._observation_bytes(path) for path in before} == before
    assert not emitted and core._LEGACY_OBSERVATION.get() is None
