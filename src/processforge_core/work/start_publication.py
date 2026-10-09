"""Publish an already permitted Work start through existing ordered operations."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Protocol


class StartEventWriter(Protocol):
    def __call__(self, event_type: str, run: dict[str, Any], assignment: dict[str, Any], stage_id: str, *, outcome: str, previous_stage_id: str = "", next_stage_id: str = "") -> None: ...


class StartStateReader(Protocol):
    def __call__(self, *, run_id: str, assignment_id: str, session_id: str) -> dict[str, Any]: ...


@dataclass(frozen=True, kw_only=True)
class WorkStartPublicationService:
    run_path: Callable[[], Callable[[str], Path]] = field(repr=False, compare=False)
    assignment_path: Callable[[], Callable[[str], Path]] = field(repr=False, compare=False)
    atomic_yaml: Callable[[], Callable[[Path, dict[str, Any]], Any]] = field(repr=False, compare=False)
    atomic_text: Callable[[], Callable[[Path, str], Any]] = field(repr=False, compare=False)
    write_task_index: Callable[[], Callable[[dict[str, Any]], Any]] = field(repr=False, compare=False)
    emit: Callable[[], StartEventWriter] = field(repr=False, compare=False)
    state: Callable[[], StartStateReader] = field(repr=False, compare=False)
    write_projection: Callable[[], Callable[[dict[str, Any]], Any]] = field(repr=False, compare=False)

    def publish(self, *, run_id: str, assignment_id: str, run: dict[str, Any], assignment: dict[str, Any], stage_id: str, objective: str, stages: list[dict[str, Any]], stage_override: str, session_id: str) -> dict[str, Any]:
        run_path = self.run_path()(run_id)
        assignment_path = self.assignment_path()(assignment_id)
        self.atomic_yaml()(run_path, run)
        self.atomic_yaml()(assignment_path, assignment)
        self.atomic_text()(run_path.parent / "plan.md", f"# Run Plan: {objective[:80]}\n\nObjective: {objective}\n")
        self.write_task_index()(run)
        self.emit()("run.created", run, assignment, stage_id, outcome="started")
        self.emit()("task.created", run, assignment, stage_id, outcome="started")
        self.emit()("assignment.created", run, assignment, stage_id, outcome="started")
        self.emit()("process.stage.started", run, assignment, stage_id, outcome="started", previous_stage_id="", next_stage_id=stage_id)
        state = self.state()(run_id=run_id, assignment_id=assignment_id, session_id=session_id)
        self.write_projection()(state)
        return {
            "schema_version": 1,
            "kind": "pf.work.start",
            "action": "created_new",
            "project": state.get("project", {}),
            "run_id": run_id,
            "assignment_id": assignment_id,
            "stage": stage_id,
            "valid_stages": [str(item.get("id")) for item in stages],
            "stage_selection": "preferred" if stage_override else "process_initial_stage",
            "session": {"status": "bound", "id": session_id} if session_id else {"status": "absent"},
            "obligations": state.get("obligations", []),
            "gates": state.get("gates", {}),
            "work_state": state,
            "context": state.get("context", {}),
        }
