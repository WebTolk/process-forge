"""Publish an already permitted Work transition through existing operations."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
import json
from pathlib import Path
from typing import Any


@dataclass(frozen=True, kw_only=True)
class WorkTransitionCommitService:
    now_utc: Callable[[], str] = field(repr=False, compare=False)
    set_run_task_status: Callable[[dict[str, Any], str, str], Any] = field(repr=False, compare=False)
    assignment_path: Callable[[str], Path] = field(repr=False, compare=False)
    run_path: Callable[[str], Path] = field(repr=False, compare=False)
    atomic_yaml: Callable[[Path, dict[str, Any]], Any] = field(repr=False, compare=False)
    write_task_index: Callable[[dict[str, Any]], Any] = field(repr=False, compare=False)
    build_completion_intent: Callable[..., dict[str, Any]] = field(repr=False, compare=False)
    completion_intent_path: Callable[[str], Path] = field(repr=False, compare=False)
    atomic_text: Callable[[Path, str], Any] = field(repr=False, compare=False)
    replay_completion_intent: Callable[..., dict[str, Any]] = field(repr=False, compare=False)
    state: Callable[..., dict[str, Any]] = field(repr=False, compare=False)
    write_projection: Callable[[dict[str, Any]], Any] = field(repr=False, compare=False)
    emit: Callable[..., Any] = field(repr=False, compare=False)
    next_work_advisory: Callable[[dict[str, Any], dict[str, Any]], dict[str, Any]] = field(repr=False, compare=False)

    def commit(
        self,
        run: dict[str, Any],
        assignment: dict[str, Any],
        process: dict[str, Any],
        *,
        stage_id: str,
        next_stage_id: str,
        outcome: str,
        notes: str,
        session_id: str,
    ) -> dict[str, Any]:
        # Admission and the enclosing run lock remain with the caller.
        now = self.now_utc()
        history = assignment.get("stage_history") if isinstance(assignment.get("stage_history"), list) else []
        history.append(
            {
                "stage_id": stage_id,
                "status": "completed",
                "started_at": str(assignment["stage_execution"].get("started_at") or assignment.get("created_at") or ""),
                "completed_at": now,
                "outcome": outcome,
                "next_stage_id": next_stage_id,
                "evidence": list(assignment["stage_execution"].get("evidence") or []),
                "notes": str(notes or ""),
            }
        )
        assignment["stage_history"] = history
        previous_stage_id = stage_id
        if next_stage_id:
            assignment["stage"] = next_stage_id
            assignment["stage_status"] = "in_progress"
            assignment["stage_execution"] = {"started_at": now, "evidence": [], "notes": ""}
            assignment["updated_at"] = now
            run["updated_at"] = now
            self.set_run_task_status(run, str(assignment["id"]), "in_progress")
            self.atomic_yaml(self.assignment_path(str(assignment["id"])), assignment)
            self.atomic_yaml(self.run_path(str(run["id"])), run)
            self.write_task_index(run)
            action = "stage_transitioned"
        else:
            intent = self.build_completion_intent(
                run,
                assignment,
                process,
                outcome=outcome,
                notes=notes,
                completed_at=now,
            )
            # JSON is valid YAML and preserves multiline payloads exactly;
            # the generic YAML formatter folds quoted multiline strings.
            self.atomic_text(self.completion_intent_path(str(run["id"])), json.dumps(intent, ensure_ascii=False, sort_keys=True, indent=2) + "\n")
            self.replay_completion_intent(intent, session_id=session_id)
            action = "run_completed"

        result_state = self.state(run_id=str(run["id"]), assignment_id=str(assignment["id"]), session_id=session_id)
        if action != "run_completed":
            self.write_projection(result_state)
            self.emit("process.stage.completed", run, assignment, previous_stage_id, outcome=outcome, previous_stage_id=previous_stage_id, next_stage_id=next_stage_id)
            self.emit("process.stage.transitioned", run, assignment, next_stage_id or previous_stage_id, outcome=outcome, previous_stage_id=previous_stage_id, next_stage_id=next_stage_id)
            if next_stage_id:
                self.emit("process.stage.started", run, assignment, next_stage_id, outcome="started", previous_stage_id=previous_stage_id, next_stage_id=next_stage_id)
        result = {**result_state, "action": action, "previous_stage_id": previous_stage_id, "next_stage_id": next_stage_id}
        if action == "run_completed":
            result.update(self.next_work_advisory(process, run))
        return result
