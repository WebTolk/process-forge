"""Existing CompletionIntentValidationService responsibilities with explicit operation dependencies."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable


@dataclass(frozen=True, kw_only=True)
class CompletionIntentValidationService:
    project_root: Path = field(repr=False, compare=False)
    fingerprint: Callable[[Any], str] = field(repr=False, compare=False)
    terminal_assignment_statuses: Callable[[], set[str]] = field(
        repr=False, compare=False
    )
    effective_process: Callable[[dict[str, Any]], tuple[dict[str, Any], str]] = field(
        repr=False, compare=False
    )
    rel: Callable[[Path, Path], str] = field(repr=False, compare=False)
    run_path: Callable[[str], Path] = field(repr=False, compare=False)
    assignment_path: Callable[[str], Path] = field(repr=False, compare=False)
    flow_root: Callable[[], Path] = field(repr=False, compare=False)
    has_project_id: Callable[[], bool] = field(repr=False, compare=False)
    project_id: Callable[[Path], Any] = field(repr=False, compare=False)

    def validate(
        self,
        intent: Any,
        run: dict[str, Any],
        assignment: dict[str, Any],
        journal_path: Path,
    ) -> str | None:
        if (
            not isinstance(intent, dict)
            or intent.get("kind") != "pf.process.completion-intent"
        ):
            return "journal kind is invalid"
        content = {key: value for key, value in intent.items() if key != "fingerprint"}
        try:
            if intent.get("fingerprint") != self.fingerprint(content):
                return "journal content fingerprint mismatch"
        except (
            TypeError,
            ValueError,
            RecursionError,
        ):
            return "journal content is invalid"
        run_id = str(run.get("id") or "")
        assignment_id = str(assignment.get("id") or "")
        if (
            intent.get("run_id") != run_id
            or intent.get("assignment_id") != assignment_id
        ):
            return "journal identity does not match selected work"
        raw_final = intent.get("final")
        final = raw_final if isinstance(raw_final, dict) else {}
        raw_run = final.get("run")
        final_run = raw_run if isinstance(raw_run, dict) else {}
        raw_assignment = final.get("assignment")
        final_assignment = raw_assignment if isinstance(raw_assignment, dict) else {}
        if (
            final_run.get("id") != run_id
            or final_assignment.get("id") != assignment_id
            or final_assignment.get("run_id") != run_id
        ):
            return "journal final payload identity is invalid"
        transition = intent.get("transition")
        if transition is not None:
            error = self._validate_transition(
                intent, run, assignment, final_run, final_assignment
            )
            if error:
                return error
        elif (
            final_run.get("status") != "completed"
            or final_assignment.get("status") not in self.terminal_assignment_statuses()
        ):
            return "journal final payload is not terminal"
        if transition is None and final_assignment.get("status") != "done":
            return "journal final assignment is not done"
        raw_tasks = final_run.get("tasks")
        tasks = raw_tasks if isinstance(raw_tasks, list) else []
        task = next(
            (
                item
                for item in tasks
                if isinstance(item, dict) and str(item.get("id") or "") == assignment_id
            ),
            None,
        )
        expected_task_statuses = (
            {"in_progress"} if transition is not None else {"done", "completed"}
        )
        if (
            not isinstance(task, dict)
            or task.get("status") not in expected_task_statuses
        ):
            return "journal final task status is invalid"
        if self.effective_process(final_run)[1] != "pinned":
            return "journal final process pin is invalid"
        raw_pin = intent.get("process_execution")
        pin = raw_pin if isinstance(raw_pin, dict) else {}
        raw_current_pin = run.get("process_execution")
        current_pin = raw_current_pin if isinstance(raw_current_pin, dict) else {}
        for key in [
            "process_id",
            "process_version",
            "process_fingerprint",
            "snapshot_id",
            "snapshot_checksum",
        ]:
            if str(pin.get(key) or "") != str(current_pin.get(key) or "") or str(
                pin.get(key) or ""
            ) != str((final_run.get("process_execution") or {}).get(key) or ""):
                return f"journal process pin mismatch: {key}"
        expected = {
            "journal_path": self.rel(journal_path, self.project_root),
            "run_path": self.rel(self.run_path(run_id), self.project_root),
            "assignment_path": self.rel(
                self.assignment_path(assignment_id), self.project_root
            ),
        }
        if str(intent.get("journal_path") or "") != expected["journal_path"]:
            return "journal path is not owned by the selected run"
        raw_owner = intent.get("owner")
        owner = raw_owner if isinstance(raw_owner, dict) else {}
        if (
            owner.get("run_path") != expected["run_path"]
            or owner.get("assignment_path") != expected["assignment_path"]
        ):
            return "journal owner paths are invalid"
        if self.has_project_id() and str(owner.get("project_id") or "") != str(
            self.project_id(self.project_root)
        ):
            return "journal project owner is invalid"
        final_paths = {
            "summary": self.rel(
                self.run_path(run_id).parent / "summary.md", self.project_root
            ),
            "handoff": self.rel(
                self.flow_root() / "handoffs" / "runs" / f"{run_id}-handoff.md",
                self.project_root,
            ),
            "task_index": self.rel(
                self.run_path(run_id).parent / "task-index.md", self.project_root
            ),
            "projection": self.rel(
                self.flow_root()
                / "artifacts"
                / "projections"
                / "process-execution-state.json",
                self.project_root,
            ),
        }
        if transition is not None:
            del final_paths["summary"], final_paths["handoff"]
        for key, expected_path in final_paths.items():
            raw_item = final.get(key)
            item = raw_item if isinstance(raw_item, dict) else {}
            if str(item.get("path") or "") != expected_path:
                return f"journal {key} path is invalid"
        events = final.get("events")
        if (
            not isinstance(events, list)
            or not events
            or any(
                (
                    not isinstance(item, dict)
                    or not item.get("event_type")
                    or (not item.get("event_id"))
                    for item in events
                )
            )
        ):
            return "journal event metadata is invalid"
        if transition is None:
            return self._validate_terminal(
                intent, run, assignment, final_run, final_assignment
            )
        return None

    def _validate_terminal(
        self,
        intent: dict[str, Any],
        run: dict[str, Any],
        assignment: dict[str, Any],
        final_run: dict[str, Any],
        final_assignment: dict[str, Any],
    ) -> str | None:
        from ..process_execution import (
            ACTIVE_ASSIGNMENT_STATUSES,
            ACTIVE_RUN_STATUSES,
            normalized_outcomes,
        )

        stage_id = final_assignment.get("stage")
        completed_at = intent.get("completed_at")
        history = final_assignment.get("stage_history")
        if (
            not isinstance(stage_id, str)
            or not stage_id
            or not isinstance(completed_at, str)
            or not completed_at
            or not isinstance(history, list)
            or not history
        ):
            return "journal terminal history is invalid"
        entry = history[-1]
        if (
            not isinstance(entry, dict)
            or entry.get("stage_id") != stage_id
            or entry.get("status") != "completed"
            or entry.get("next_stage_id") != ""
            or entry.get("completed_at") != completed_at
            or final_assignment.get("stage_status") != "completed"
            or final_assignment.get("updated_at") != completed_at
            or final_run.get("updated_at") != completed_at
        ):
            return "journal terminal payload is invalid"
        outcome = entry.get("outcome")
        if not isinstance(outcome, str) or not outcome:
            return "journal terminal outcome is invalid"
        process, pin_status = self.effective_process(final_run)
        try:
            allowed = (
                normalized_outcomes(process, stage_id) if pin_status == "pinned" else []
            )
        except ValueError:
            return "journal terminal process is invalid"
        outcomes = {str(item.get("id")): item for item in allowed}
        if outcome not in outcomes or str(outcomes[outcome].get("next_stage") or ""):
            return "journal terminal outcome is not allowed by pinned process"
        current_history = assignment.get("stage_history") or []
        before_assignment = (
            assignment.get("stage") == stage_id
            and str(assignment.get("status") or "") in ACTIVE_ASSIGNMENT_STATUSES
            and assignment.get("stage_status") == "in_progress"
            and current_history == history[:-1]
        )
        if not before_assignment and assignment != final_assignment:
            return "journal terminal assignment does not match selected history"
        if str(run.get("status") or "") in ACTIVE_RUN_STATUSES:
            tasks = run.get("tasks")
            matching = (
                [
                    task
                    for task in tasks
                    if isinstance(task, dict) and task.get("id") == assignment.get("id")
                ]
                if isinstance(tasks, list)
                else []
            )
            if (
                len(matching) != 1
                or str(matching[0].get("status") or "")
                not in ACTIVE_ASSIGNMENT_STATUSES
            ):
                return "journal terminal task does not match selected work"
        elif run != final_run:
            return "journal terminal run does not match selected work"
        intent_seed = ":".join(
            [
                str(run.get("id") or ""),
                str(assignment.get("id") or ""),
                completed_at,
                outcome,
            ]
        )
        intent_id = (
            "completion-" + hashlib.sha256(intent_seed.encode("utf-8")).hexdigest()[:32]
        )
        if intent.get("intent_id") != intent_id:
            return "journal terminal identity is invalid"
        expected = []
        for event_type in [
            "process.stage.completed",
            "process.stage.transitioned",
            "task.completed",
            "assignment.completed",
            "run.completed",
            "run.summary.created",
        ]:
            event_id = (
                "evt_"
                + hashlib.sha256(
                    (intent_id + ":" + event_type).encode("utf-8")
                ).hexdigest()[:32]
            )
            expected.append(
                {
                    "event_type": event_type,
                    "event_id": event_id,
                    "stage_id": stage_id,
                    "previous_stage_id": stage_id,
                    "next_stage_id": "",
                    "outcome": outcome,
                }
            )
        if intent["final"].get("events") != expected:
            return "journal terminal event metadata is invalid"
        return None

    def _validate_transition(
        self,
        intent: dict[str, Any],
        run: dict[str, Any],
        assignment: dict[str, Any],
        final_run: dict[str, Any],
        final_assignment: dict[str, Any],
    ) -> str | None:
        from ..process_execution import normalized_outcomes

        transition = intent["transition"]
        if not isinstance(transition, dict):
            return "journal transition is invalid"
        previous, following = (
            transition.get("previous_stage_id"),
            transition.get("next_stage_id"),
        )
        outcome = transition.get("outcome")
        history = final_assignment.get("stage_history")
        if (
            not isinstance(previous, str)
            or not previous
            or not isinstance(following, str)
            or not following
            or not isinstance(outcome, str)
            or not outcome
            or not isinstance(history, list)
            or not history
            or transition.get("history_length") != len(history)
        ):
            return "journal transition identity is invalid"
        entry = history[-1]
        if (
            not isinstance(entry, dict)
            or entry.get("stage_id") != previous
            or entry.get("next_stage_id") != following
            or entry.get("outcome") != outcome
            or entry.get("status") != "completed"
            or entry.get("completed_at") != intent.get("completed_at")
        ):
            return "journal transition history is invalid"
        if (
            final_run.get("status") != run.get("status")
            or final_run.get("status")
            not in {"draft", "open", "in_progress", "blocked", "review"}
            or final_assignment.get("status") != assignment.get("status")
            or final_assignment.get("status") in self.terminal_assignment_statuses()
            or final_assignment.get("stage") != following
            or final_assignment.get("stage_status") != "in_progress"
            or final_assignment.get("stage_execution")
            != {"started_at": intent.get("completed_at"), "evidence": [], "notes": ""}
            or final_run.get("updated_at") != intent.get("completed_at")
            or final_assignment.get("updated_at") != intent.get("completed_at")
        ):
            return "journal nonterminal payload is invalid"
        current_history = assignment.get("stage_history") or []
        if not (
            (current_history == history[:-1] and assignment.get("stage") == previous)
            or (current_history == history and assignment.get("stage") == following)
        ):
            return "journal transition does not match selected history"
        process, pin_status = self.effective_process(final_run)
        try:
            allowed = (
                normalized_outcomes(process, previous) if pin_status == "pinned" else []
            )
        except ValueError:
            return "journal transition process is invalid"
        if not any(
            item["id"] == outcome and item["next_stage"] == following
            for item in allowed
        ):
            return "journal transition is not allowed by pinned process"
        expected = []
        for event_type, stage, event_outcome in [
            ("process.stage.completed", previous, outcome),
            ("process.stage.transitioned", following, outcome),
            ("process.stage.started", following, "started"),
        ]:
            import hashlib

            event_id = (
                "evt_"
                + hashlib.sha256(
                    f"{intent.get('intent_id')}:{event_type}".encode("utf-8")
                ).hexdigest()[:32]
            )
            expected.append(
                {
                    "event_type": event_type,
                    "event_id": event_id,
                    "stage_id": stage,
                    "previous_stage_id": previous,
                    "next_stage_id": following,
                    "outcome": event_outcome,
                }
            )
        if intent["final"].get("events") != expected:
            return "journal transition event metadata is invalid"
        return None
