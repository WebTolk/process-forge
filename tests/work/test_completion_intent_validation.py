"""Refuse incompatible terminal recovery without rewriting records or SQL facts."""

from __future__ import annotations

import copy
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import processforge as core
import pytest
import yaml
from process_execution_smoke_support import stage_evidence
from work.test_complete_admission import final_stage, make_work

from processforge_core.agents.process_events import ProcessEventRecorder
from processforge_core.process_execution import (
    ProcessExecutionService,
    canonical_fingerprint,
)
from processforge_core.work.consistency import RunTaskInputReader


@dataclass(frozen=True)
class PendingCompletion:
    project: Path
    workplace: Path
    selection: dict[str, str]
    intent: dict[str, Any]

    @property
    def intent_path(self) -> Path:
        return (
            self.project
            / ".pf/runs"
            / self.selection["run_id"]
            / "completion-intent.yaml"
        )

    @property
    def assignment_path(self) -> Path:
        return (
            self.project
            / ".pf/assignments"
            / (self.selection["assignment_id"] + ".yaml")
        )

    @property
    def run_path(self) -> Path:
        return self.intent_path.parent / "run.yaml"


def pending_completion(
    root: Path, monkeypatch: pytest.MonkeyPatch, checkpoint: str = "assignment-before"
) -> PendingCompletion:
    service, selection, project, workplace = make_work(root)
    final_stage(service, selection)
    intent_path = project / ".pf/runs" / selection["run_id"] / "completion-intent.yaml"
    target = (
        project / ".pf/assignments" / (selection["assignment_id"] + ".yaml")
        if checkpoint.startswith("assignment")
        else intent_path.parent / "run.yaml"
    )
    original_text = ProcessExecutionService._atomic_text
    original_emit = ProcessEventRecorder.emit_process_event
    interrupted = False

    def atomic(owner: Any, path: Path, content: str) -> None:
        nonlocal interrupted
        if (
            owner is service
            and path == target
            and intent_path.exists()
            and not interrupted
        ):
            interrupted = True
            if checkpoint.endswith("after"):
                original_text(owner, path, content)
            raise OSError("fixture terminal replay interrupted")
        original_text(owner, path, content)

    def emit(owner: Any, project_root: Path, event_type: str, **parameters: Any) -> Any:
        nonlocal interrupted
        result = original_emit(owner, project_root, event_type, **parameters)
        if (
            project_root == project
            and event_type == "run.completed"
            and not interrupted
        ):
            interrupted = True
            raise OSError("fixture terminal replay interrupted")
        return result

    with monkeypatch.context() as fault:
        if checkpoint == "event-after":
            fault.setattr(ProcessEventRecorder, "emit_process_event", emit)
        else:
            fault.setattr(ProcessExecutionService, "_atomic_text", atomic)
        with pytest.raises(OSError, match="fixture terminal replay interrupted"):
            service.complete(
                **selection,
                evidence=stage_evidence("report", "verify-ready"),
                notes="original terminal completion",
            )
    assert interrupted and intent_path.is_file()
    return PendingCompletion(
        project, workplace, selection, yaml.safe_load(intent_path.read_bytes())
    )


def events(case: PendingCompletion) -> list[dict[str, Any]]:
    runtime = RunTaskInputReader().event_runtime_paths(case.project)[0]
    assert runtime.resolve().is_relative_to(case.project.resolve())
    rows = list(core.iter_process_events(runtime))
    assert all(error is None for _sequence, _event, error in rows), rows
    return [event for _sequence, event, _error in rows]


def durable_bytes(case: PendingCompletion) -> dict[str, bytes]:
    return {
        prefix + "/" + path.relative_to(root).as_posix(): path.read_bytes()
        for prefix, root in [
            ("project", case.project / ".pf"),
            ("workplace", case.workplace),
        ]
        for path in root.rglob("*")
        if path.is_file() and not path.name.endswith((".lock", ".guard"))
    }


def write_document(path: Path, value: dict[str, Any]) -> None:
    path.write_text(
        json.dumps(value, sort_keys=True, indent=2) + "\n", encoding="utf-8"
    )


def write_intent(case: PendingCompletion, intent: dict[str, Any]) -> None:
    intent["fingerprint"] = canonical_fingerprint(
        {key: value for key, value in intent.items() if key != "fingerprint"}
    )
    write_document(case.intent_path, intent)


def recovered(case: PendingCompletion, entrypoint: str = "complete") -> None:
    service = core.process_execution_service(case.project, str(case.workplace))
    result = getattr(service, entrypoint)(
        **case.selection, outcome="ignored-invalid-retry", notes="ignored retry"
    )
    assert result["action"] == "run_completed", result
    assert not case.intent_path.exists()
    assert (
        yaml.safe_load(case.assignment_path.read_bytes())
        == case.intent["final"]["assignment"]
    )
    assert yaml.safe_load(case.run_path.read_bytes()) == case.intent["final"]["run"]
    rows = events(case)
    for spec in case.intent["final"]["events"]:
        assert sum(event.get("event_id") == spec["event_id"] for event in rows) == 1


def refuse_then_restore(
    case: PendingCompletion, original: dict[Path, bytes], entrypoint: str
) -> None:
    service = core.process_execution_service(case.project, str(case.workplace))
    before_events = events(case)
    before = durable_bytes(case)
    result = getattr(service, entrypoint)(**case.selection, outcome="completed")
    assert result["action"] == "blocked", result
    assert result["reason"] == "completion_intent_invalid", result
    assert case.intent_path.is_file()
    assert events(case) == before_events
    assert durable_bytes(case) == before
    for path, content in original.items():
        path.write_bytes(content)
    recovered(case, entrypoint)


@pytest.mark.parametrize(
    "corruption,entrypoint",
    [
        ("assignment-cancelled", "complete"),
        ("assignment-failed", "transition"),
        ("run-cancelled", "complete"),
        ("run-failed", "transition"),
        ("task-cancelled", "complete"),
        ("stage-rewound", "transition"),
        ("history-diverged", "complete"),
        ("history-edited", "transition"),
        ("assignment-incomplete-terminal", "complete"),
        ("run-incomplete-terminal", "transition"),
    ],
)
def test_terminal_intent_refuses_incompatible_current_records(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, corruption: str, entrypoint: str
) -> None:
    case = pending_completion(tmp_path, monkeypatch)
    original = {
        path: path.read_bytes() for path in [case.assignment_path, case.run_path]
    }
    assignment = yaml.safe_load(original[case.assignment_path])
    run = yaml.safe_load(original[case.run_path])
    if corruption.startswith("assignment-"):
        assignment["status"] = (
            "done" if corruption.endswith("terminal") else corruption.split("-")[1]
        )
    elif corruption.startswith("run-"):
        run["status"] = (
            "completed" if corruption.endswith("terminal") else corruption.split("-")[1]
        )
    elif corruption == "task-cancelled":
        next(
            task
            for task in run["tasks"]
            if task["id"] == case.selection["assignment_id"]
        )["status"] = "cancelled"
    elif corruption == "stage-rewound":
        assignment["stage"] = "prepare"
    elif corruption == "history-diverged":
        assignment["stage_history"].append(
            {"stage_id": "unexpected", "status": "completed"}
        )
    else:
        assignment["stage_history"][0]["outcome"] = "unexpected"
    write_document(case.assignment_path, assignment)
    write_document(case.run_path, run)
    refuse_then_restore(case, original, entrypoint)


@pytest.mark.parametrize(
    "corruption",
    [
        "missing",
        "duplicate",
        "type",
        "id",
        "stage",
        "previous",
        "next",
        "outcome",
        "order",
        "intent-id",
        "empty",
    ],
)
def test_terminal_intent_refuses_corrupted_events(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, corruption: str
) -> None:
    case = pending_completion(tmp_path, monkeypatch)
    original = {case.intent_path: case.intent_path.read_bytes()}
    intent = copy.deepcopy(case.intent)
    specifications = intent["final"]["events"]
    if corruption == "missing":
        specifications[:] = [
            event for event in specifications if event["event_type"] != "run.completed"
        ]
    elif corruption == "duplicate":
        specifications.append(copy.deepcopy(specifications[-1]))
    elif corruption == "empty":
        specifications.clear()
    elif corruption == "order":
        specifications.reverse()
    elif corruption == "intent-id":
        intent["intent_id"] = "completion-" + "0" * 32
        for event in specifications:
            event["event_id"] = (
                "evt_"
                + hashlib.sha256(
                    (intent["intent_id"] + ":" + event["event_type"]).encode("utf-8")
                ).hexdigest()[:32]
            )
    else:
        field = {
            "type": "event_type",
            "id": "event_id",
            "stage": "stage_id",
            "previous": "previous_stage_id",
            "next": "next_stage_id",
            "outcome": "outcome",
        }[corruption]
        specifications[-1][field] = "substituted"
    write_intent(case, intent)
    refuse_then_restore(
        case,
        original,
        "transition" if corruption in {"id", "stage", "next"} else "complete",
    )


@pytest.mark.parametrize(
    "corruption",
    [
        "missing-history",
        "history-stage",
        "history-outcome",
        "history-next",
        "assignment-time",
        "run-time",
    ],
)
def test_terminal_intent_refuses_inconsistent_final_payload(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, corruption: str
) -> None:
    case = pending_completion(tmp_path, monkeypatch)
    original = {case.intent_path: case.intent_path.read_bytes()}
    intent = copy.deepcopy(case.intent)
    assignment = intent["final"]["assignment"]
    if corruption == "missing-history":
        assignment["stage_history"].clear()
    elif corruption.startswith("history-"):
        field = {
            "history-stage": "stage_id",
            "history-outcome": "outcome",
            "history-next": "next_stage_id",
        }[corruption]
        assignment["stage_history"][-1][field] = "unexpected"
    elif corruption == "assignment-time":
        assignment["updated_at"] = "unexpected"
    else:
        intent["final"]["run"]["updated_at"] = "unexpected"
    write_intent(case, intent)
    refuse_then_restore(case, original, "complete")


@pytest.mark.parametrize(
    "checkpoint", ["assignment-before", "assignment-after", "run-after", "event-after"]
)
def test_terminal_intent_accepts_valid_partial_replay(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, checkpoint: str
) -> None:
    case = pending_completion(tmp_path, monkeypatch, checkpoint)
    recovered(case)
