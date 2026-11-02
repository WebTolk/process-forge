"""Start admission, interruption recovery and immutable Work identities."""

from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest
import yaml

from processforge_core.agents.hook_dispatch import RuntimeHookDispatcher
from processforge_core.agents.hook_policy import HookDispatchPolicy
from processforge_core.agents.process_events import ProcessEventRecorder
from processforge_core.configuration import ConfigurationProvider, PFConfig
from processforge_core.executions.model import ExecutionError
from processforge_core.process_event_journal import ProcessEventJournal
from processforge_core.runtime.execution_admission import ExecutionAdmission
from processforge_core.work.capsule_publication import publish_capsule_bytes
from processforge_core.work.start_intent import (
    RENDERING_START,
    StartIntentError,
    applied,
    find_pending,
    intent_path,
    pending_reason,
    read_record,
)
from processforge_core.work.start_publication import WorkStartPublicationService


class Journal(ProcessEventJournal):
    """Real SQLite journal; the unit fixture has no migration enrollment."""


class PublicationCase:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.flow = root / ".pf"
        self.flow.mkdir(parents=True)
        (self.flow / "process-forge.yaml").write_text(
            "schema_version: 1\nproject:\n  id: fixture\n", encoding="utf-8"
        )
        self.run_path = self.flow / "runs/run/run.yaml"
        self.assignment_path = self.flow / "assignments/task.yaml"
        self.capsule = self.flow / "contexts/assignment-capsules/task.capsule.yaml"
        self.recorder = ProcessEventRecorder(
            journal=Journal(), configuration=ConfigurationProvider.pinned(PFConfig())
        )
        self.capsule_text = "capsule: immutable exact fixture bytes\n"
        pin = {
            "assignment_capsule": ".pf/contexts/assignment-capsules/task.capsule.yaml",
            "assignment_capsule_checksum": "sha256:"
            + hashlib.sha256(self.capsule_text.encode()).hexdigest(),
        }
        self.run = {
            "id": "run",
            "objective": "Create exact Work",
            "status": "in_progress",
            "created_at": "2026-11-02T00:00:00Z",
            "process_execution": pin,
        }
        self.assignment = {
            "id": "task",
            "run_id": "run",
            "objective": self.run["objective"],
            "status": "in_progress",
            "stage": "prepare",
            "process_execution": pin,
        }
        self.fail_target = ""
        self.fail_when = ""
        self.failed = False
        self.state_admission: list[bool] = []

    def atomic_text(self, path: Path, content: str) -> None:
        target = path.name
        inject = target == self.fail_target and not self.failed
        if inject and self.fail_when == "before":
            self.failed = True
            raise OSError("injected publication failure")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        if inject:
            self.failed = True
            raise OSError("injected publication failure")

    def state(self, **selectors: Any) -> dict[str, Any]:
        self.state_admission.append(ExecutionAdmission.held(self.root, None))
        reason = pending_reason(self.run_path, "fixture")
        return {
            "project": {"id": "fixture"},
            "execution_readiness": {"status": "blocked" if reason else "ready"},
            "blockers": [reason] if reason else [],
        }

    def emit(
        self,
        event_type: str,
        run: dict[str, Any],
        assignment: dict[str, Any],
        stage_id: str,
        *,
        outcome: str,
        previous_stage_id: str = "",
        next_stage_id: str = "",
        event_id: str | None = None,
    ) -> None:
        self.recorder.emit_process_event(
            self.root,
            event_type,
            assignment_id_value=assignment["id"],
            correlation_id="run-run",
            stage=stage_id,
            payload={"run_id": run["id"], "outcome": outcome},
            event_id=event_id,
        )

    def service(self) -> WorkStartPublicationService:
        return WorkStartPublicationService(
            run_path=lambda: lambda _: self.run_path,
            assignment_path=lambda: lambda _: self.assignment_path,
            atomic_yaml=lambda: (
                lambda path, value: self.atomic_text(path, yaml.safe_dump(value))
            ),
            atomic_text=lambda: self.atomic_text,
            write_task_index=lambda: (
                lambda _: self.atomic_text(
                    self.run_path.with_name("task-index.md"), "exact index\n"
                )
            ),
            emit=lambda: self.emit,
            state=lambda: self.state,
            write_projection=lambda: (
                lambda value: self.atomic_text(
                    self.flow / "artifacts/projections/process-execution-state.json",
                    json.dumps(value),
                )
            ),
        )

    def admission(self):
        return self.recorder.publication(
            self.root, None, event_time=str(self.run["created_at"])
        )

    def start(self):
        return self.service().publish(
            run_id="run",
            assignment_id="task",
            run=copy.deepcopy(self.run),
            assignment=copy.deepcopy(self.assignment),
            stage_id="prepare",
            objective=str(self.run["objective"]),
            stages=[{"id": "prepare"}],
            stage_override="",
            session_id="",
            project_id="fixture",
            capsule_text=self.capsule_text,
            request={},
            admission=self.admission,
        )

    def recover(self):
        intent = find_pending(self.flow, str(self.run["objective"]), "fixture")
        assert intent is not None
        return self.service().replay(intent, session_id="", admission=self.admission)

    def event_ids(self):
        path = self.recorder.inputs.event_runtime_paths(self.root)[0]
        with self.recorder.journal.connection(path) as connection:
            return [
                row[0]
                for row in connection.execute(
                    "SELECT event_id FROM admissions ORDER BY seq"
                )
            ]


@pytest.fixture
def case(tmp_path, monkeypatch):
    monkeypatch.setattr(HookDispatchPolicy, "selected_hooks", lambda *_: [])
    return PublicationCase(tmp_path / "project")


def test_admission_failure_precedes_all_authoritative_work(case, monkeypatch):
    failure = ExecutionError("execution_activity_unknown")
    monkeypatch.setattr(ExecutionAdmission, "start", lambda *a, **kw: _Refused(failure))
    with pytest.raises(ExecutionError) as caught:
        case.start()
    assert caught.value is failure
    assert not case.run_path.exists()
    assert not case.assignment_path.exists()
    assert not case.capsule.exists()
    assert not intent_path(case.run_path).exists()


class _Refused:
    def __init__(self, failure):
        self.failure = failure

    def __enter__(self):
        raise self.failure

    def __exit__(self, *_):
        return None


@pytest.mark.parametrize(
    "target",
    [
        "start-intent.json",
        "run.yaml",
        "task.yaml",
        "plan.md",
        "task-index.md",
        "process-execution-state.json",
        "start-applied.json",
    ],
)
@pytest.mark.parametrize("when", ["before", "after"])
def test_each_file_failure_replays_exact_identity(case, target, when):
    case.fail_target, case.fail_when = target, when
    with pytest.raises(OSError, match="injected publication failure"):
        case.start()
    if target == "start-intent.json" and when == "before":
        assert not case.capsule.exists()
        assert case.start()["run_id"] == "run"
        return
    intent = read_record(intent_path(case.run_path))
    capsule = case.capsule.read_bytes() if case.capsule.exists() else None
    if target == "start-applied.json" and when == "after":
        assert applied(intent, case.run_path)
        assert pending_reason(case.run_path, "fixture") == ""
        return
    assert pending_reason(case.run_path, "fixture") == "work_start_publication_pending"
    result = case.recover()
    assert result["run_id"] == "run" and result["assignment_id"] == "task"
    assert applied(intent, case.run_path)
    assert case.capsule.read_bytes() == (capsule or case.capsule_text.encode())
    assert len(set(case.event_ids())) == len(case.event_ids()) == 4
    assert case.state_admission and not any(case.state_admission)
    assert RENDERING_START.get() is None


@pytest.mark.parametrize("position", [1, 2, 3, 4])
def test_event_interruption_rolls_back_batch_and_replays(case, monkeypatch, position):
    original = ProcessEventRecorder.emit_process_event
    seen = 0

    def interrupted(recorder, *args, **kwargs):
        nonlocal seen
        result = original(recorder, *args, **kwargs)
        seen += 1
        if seen == position:
            raise OSError("event interruption")
        return result

    with monkeypatch.context() as local:
        local.setattr(ProcessEventRecorder, "emit_process_event", interrupted)
        with pytest.raises(OSError, match="event interruption"):
            case.start()
    assert case.event_ids() == []
    capsule = case.capsule.read_bytes()
    assert case.recover()["action"] == "created_new"
    assert case.capsule.read_bytes() == capsule
    assert len(case.event_ids()) == 4


def test_projection_failure_does_not_duplicate_dispatch(case, monkeypatch):
    monkeypatch.setattr(
        HookDispatchPolicy, "selected_hooks", lambda *_: [{"id": "hook"}]
    )
    dispatched = []
    monkeypatch.setattr(
        RuntimeHookDispatcher,
        "dispatch_hooks",
        lambda self, root, event, **kw: dispatched.append(event["event_id"]),
    )
    case.fail_target, case.fail_when = "process-execution-state.json", "before"
    with pytest.raises(OSError):
        case.start()
    ids = case.event_ids()
    assert dispatched == ids and len(ids) == 4
    case.recover()
    assert dispatched == ids


def test_changed_authoritative_bytes_refuse_replay(case):
    case.fail_target, case.fail_when = "process-execution-state.json", "before"
    with pytest.raises(OSError):
        case.start()
    case.assignment_path.write_text("other: assignment\n", encoding="utf-8")
    before = case.capsule.read_bytes()
    with pytest.raises(StartIntentError, match="work_start_concurrent_change"):
        case.recover()
    assert case.capsule.read_bytes() == before
    assert pending_reason(case.run_path, "fixture") == "work_start_publication_pending"


def test_other_project_cannot_inherit_render_bypass(case, tmp_path):
    case.fail_target, case.fail_when = "process-execution-state.json", "before"
    with pytest.raises(OSError):
        case.start()
    other = PublicationCase(tmp_path / "other")
    other.fail_target, other.fail_when = "process-execution-state.json", "before"
    with pytest.raises(OSError):
        other.start()
    intent = read_record(intent_path(case.run_path))
    token = RENDERING_START.set((str(case.run_path), intent["checksum"]))
    try:
        assert pending_reason(case.run_path, "fixture") == ""
        assert (
            pending_reason(other.run_path, "fixture")
            == "work_start_publication_pending"
        )
    finally:
        RENDERING_START.reset(token)


def test_capsule_publish_is_atomic_and_does_not_clobber(tmp_path):
    path = tmp_path / "capsule.yaml"
    with patch(
        "processforge_core.work.capsule_publication.os.link",
        side_effect=OSError("interrupted link"),
    ):
        with pytest.raises(OSError):
            publish_capsule_bytes(path, b"complete capsule\n")
    assert not path.exists() and list(tmp_path.iterdir()) == []
    publish_capsule_bytes(path, b"complete capsule\n")
    with pytest.raises(FileExistsError):
        publish_capsule_bytes(path, b"changed capsule\n")
    assert path.read_bytes() == b"complete capsule\n"


def test_real_work_retry_and_direct_worker_guard():
    import processforge as core
    from process_execution_smoke_support import fixture

    from processforge_core.composition import bind_process_events
    from processforge_core.prepared.input import semantic_input
    from processforge_core.process_execution import ProcessExecutionService

    with fixture() as (workplace, project, _started):
        service = bind_process_events(
            ProcessExecutionService(project, workplace, core), ProcessEventRecorder()
        )
        with patch.object(
            ProcessExecutionService,
            "_write_projection",
            side_effect=OSError("projection interrupted"),
        ):
            with pytest.raises(OSError, match="projection interrupted"):
                service.start(objective="Recover direct worker publication")
        paths = list((project / ".pf/runs").glob("*/start-intent.json"))
        intent = next(
            read_record(path)
            for path in paths
            if read_record(path)["objective"] == "Recover direct worker publication"
        )
        run, assignment = intent["run"], intent["assignment"]
        capsule_path = core.assignment_capsule_path(project, assignment["id"])
        capsule_bytes = capsule_path.read_bytes()
        state = service.state(run_id=run["id"], assignment_id=assignment["id"])
        assert state["execution_readiness"]["status"] == "blocked"
        assert (
            state["context"]["validation"]["reason"] == "work_start_publication_pending"
        )
        with pytest.raises(ValueError, match="work_start_publication_pending"):
            semantic_input(project, assignment, yaml.safe_load(capsule_bytes), core)
        fresh = bind_process_events(
            ProcessExecutionService(project, workplace, core), ProcessEventRecorder()
        )
        assert (
            fresh.start(objective="Different request during pending start")["reason"]
            == "work_start_publication_pending"
        )
        rejected = fresh.start(
            objective=intent["objective"],
            scope_intent={"schema_version": 1, "assignment": {}},
        )
        assert rejected["reason"] == "scope_intent_mismatch"
        result = fresh.start(objective=intent["objective"])
        assert result["run_id"] == run["id"]
        assert result["assignment_id"] == assignment["id"]
        assert capsule_path.read_bytes() == capsule_bytes
        assert (
            fresh.start(objective=intent["objective"])["action"] == "continue_existing"
        )
        assert result["context"]["validation"]["status"] == "valid"


@pytest.mark.parametrize("when", ["before", "after"])
def test_capsule_interruption_keeps_recoverable_exact_plan(case, monkeypatch, when):
    original = publish_capsule_bytes

    def interrupted(path, raw):
        if when == "after":
            original(path, raw)
        raise OSError("capsule interruption")

    with monkeypatch.context() as local:
        local.setattr(
            "processforge_core.work.start_publication.publish_capsule_bytes",
            interrupted,
        )
        with pytest.raises(OSError, match="capsule interruption"):
            case.start()
    assert intent_path(case.run_path).exists()
    assert not case.run_path.exists()
    assert case.recover()["run_id"] == "run"
    assert case.capsule.read_bytes() == case.capsule_text.encode()


def test_dispatch_failure_keeps_pending_delivery_and_exact_retry(case, monkeypatch):
    monkeypatch.setattr(
        HookDispatchPolicy, "selected_hooks", lambda *_: [{"id": "hook"}]
    )
    delivered = []

    def dispatch(self, root, event, **kw):
        delivered.append(event["event_id"])
        if len(delivered) == 1:
            raise OSError("dispatch interruption")

    monkeypatch.setattr(RuntimeHookDispatcher, "dispatch_hooks", dispatch)
    with pytest.raises(OSError, match="dispatch interruption"):
        case.start()
    ids = case.event_ids()
    assert len(ids) == 4 and len(delivered) == 1
    assert pending_reason(case.run_path, "fixture") == "work_start_publication_pending"
    case.recover()
    assert case.event_ids() == ids
    assert delivered == [ids[0], *ids]
    path = case.recorder.inputs.event_runtime_paths(case.root)[0]
    assert case.recorder.journal.pending_dispatch(path) == []


def test_corrupt_intent_cannot_bypass_pending_readiness(case):
    case.fail_target, case.fail_when = "process-execution-state.json", "before"
    with pytest.raises(OSError):
        case.start()
    path = intent_path(case.run_path)
    intent = read_record(path)
    token = RENDERING_START.set((str(case.run_path), intent["checksum"]))
    try:
        intent["assignment"]["id"] = "different"
        path.write_text(json.dumps(intent), encoding="utf-8")
        assert pending_reason(case.run_path, "fixture") == "work_start_intent_invalid"
    finally:
        RENDERING_START.reset(token)
    before = case.capsule.read_bytes()
    with pytest.raises(StartIntentError):
        case.recover()
    assert case.capsule.read_bytes() == before
