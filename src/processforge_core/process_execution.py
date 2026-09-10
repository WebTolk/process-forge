from __future__ import annotations

import contextlib
import copy
import hashlib
import json
import re
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterator


ACTIVE_RUN_STATUSES = {"draft", "open", "in_progress", "blocked", "review"}
ACTIVE_ASSIGNMENT_STATUSES = {"draft", "ready", "open", "pending", "in_progress", "blocked", "debugging", "review", "ready_for_review"}
TERMINAL_ASSIGNMENT_STATUSES = {"done", "completed", "cancelled", "failed"}
TERMINAL_RUN_STATUSES = {"completed", "cancelled", "failed"}
SAFE_ID_RE = re.compile(r"^(?:[a-z0-9]|[a-z0-9][a-z0-9-]*[a-z0-9])$")


def _stable_ids(value: Any) -> list[str]:
    values = value if isinstance(value, list) else ([] if value is None or value == "" else [value])
    result: list[str] = []
    for item in values:
        candidate = str(item.get("id") if isinstance(item, dict) else item or "").strip()
        if candidate and candidate not in result:
            result.append(candidate)
    return result


def project_process_selection(manifest: dict[str, Any]) -> dict[str, Any]:
    """Normalize legacy `process` and additive multi-process selection input."""
    legacy = str(manifest.get("process") or "").strip()
    declared = manifest.get("processes")
    if isinstance(declared, dict):
        allowed = _stable_ids(declared.get("allowed"))
        default = str(declared.get("default") or legacy or "").strip()
        return {"default": default, "allowed": allowed or ([legacy] if legacy else ["task-batch-execution"]), "source": "processes"}
    selected = legacy or "task-batch-execution"
    return {"default": selected, "allowed": [selected], "source": "legacy_process" if legacy else "fallback"}


def project_specialization_selection(manifest: dict[str, Any], process: dict[str, Any]) -> dict[str, list[str]]:
    """Keep project authorization distinct from the active Work specialization set."""
    declared = manifest.get("specializations")
    if isinstance(declared, dict):
        allowed = _stable_ids(declared.get("allowed"))
        active = _stable_ids(declared.get("active") or declared.get("default"))
        policy = process.get("specialization_policy") if isinstance(process.get("specialization_policy"), dict) else {}
        if not active:
            # A process may constrain an explicitly selected project profile,
            # but it must not invent a profile from ad-hoc legacy fields.
            active = _stable_ids(policy.get("default"))
        policy_allowed = _stable_ids(policy.get("allowed"))
        forbidden = set(_stable_ids(policy.get("forbidden")))
        return {
            "allowed": allowed,
            "active": [item for item in active if item in allowed and item not in forbidden and (not policy_allowed or item in policy_allowed)],
        }
    legacy = _stable_ids(declared)
    # A legacy list was the already-selected profile. Preserve that behaviour.
    return {"allowed": legacy, "active": legacy}


def canonical_fingerprint(value: Any) -> str:
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return "sha256:" + hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def executable_stages(process: dict[str, Any]) -> list[dict[str, Any]]:
    stages = process.get("stages") if isinstance(process.get("stages"), list) else []
    return [copy.deepcopy(item) for item in stages if isinstance(item, dict) and item.get("id") and item.get("executable", True) is not False]


def initial_stage_id(process: dict[str, Any]) -> str:
    stages = executable_stages(process)
    stage_ids = [str(item["id"]) for item in stages]
    declared = str(process.get("initial_stage") or "").strip()
    if declared:
        if declared not in stage_ids:
            raise ValueError(f"initial stage is not executable: {declared}")
        return declared
    return stage_ids[0] if stage_ids else ""


def normalized_outcomes(process: dict[str, Any], stage_id: str) -> list[dict[str, Any]]:
    stages = executable_stages(process)
    index = next((offset for offset, stage in enumerate(stages) if str(stage.get("id")) == stage_id), -1)
    if index < 0:
        return []
    default_next = str(stages[index + 1].get("id")) if index + 1 < len(stages) else ""
    raw = stages[index].get("outcomes")
    outcomes: list[dict[str, Any]] = []
    if isinstance(raw, dict):
        for outcome_id, target in raw.items():
            item = dict(target) if isinstance(target, dict) else {"next_stage": target}
            item["id"] = str(item.get("id") or outcome_id)
            outcomes.append(item)
    elif isinstance(raw, list):
        for value in raw:
            if isinstance(value, str):
                outcomes.append({"id": value})
            elif isinstance(value, dict) and value.get("id"):
                outcomes.append(copy.deepcopy(value))
    if not outcomes:
        outcomes = [{"id": "completed", "next_stage": default_next}]
    stage_ids = {str(item.get("id")) for item in stages}
    normalized: list[dict[str, Any]] = []
    for item in outcomes:
        outcome_id = str(item.get("id") or "").strip()
        if not outcome_id:
            continue
        next_stage = str(item.get("next_stage") or default_next).strip()
        if next_stage and next_stage not in stage_ids:
            raise ValueError(f"outcome {outcome_id} routes to an unknown stage: {next_stage}")
        normalized.append({"id": outcome_id, "next_stage": next_stage, "title": str(item.get("title") or outcome_id)})
    return normalized


@dataclass(frozen=True)
class ProcessExecutionService:
    project_root: Path
    workplace_root: Path | None
    core: Any

    def start(self, *, objective: str, process_id: str = "", session_id: str = "", stage_override: str = "") -> dict[str, Any]:
        with self._start_lock():
            return self._start_locked(objective=objective, process_id=process_id, session_id=session_id, stage_override=stage_override)

    def _start_locked(self, *, objective: str, process_id: str = "", session_id: str = "", stage_override: str = "") -> dict[str, Any]:
        objective = str(objective or "").strip()
        if not objective:
            return self._blocked("objective_required")
        check = self._context_check()
        if str(check.get("status") or "") not in {"fresh", "fresh_with_updates"}:
            return self._blocked(
                "snapshot_not_fresh",
                context={"status": check.get("status"), "recommended_action": check.get("recommended_action")},
            )
        duplicate = self._find_by_objective(objective)
        if duplicate.get("active"):
            state = self.state(
                run_id=str(duplicate["active"].get("run_id") or ""),
                assignment_id=str(duplicate["active"].get("assignment_id") or ""),
                session_id=session_id,
            )
            return {
                "schema_version": 1,
                "kind": "pf.work.start",
                "action": "continue_existing",
                "project": state.get("project", {}),
                "run_id": state.get("run", {}).get("id"),
                "assignment_id": state.get("assignment", {}).get("id"),
                "stage": state.get("stage", {}).get("id"),
                "session": {"status": "bound", "id": session_id} if session_id else {"status": "absent"},
                "work_state": state,
            }
        if duplicate.get("historical"):
            return self._blocked(
                "completed_historical_work_matches_objective",
                action="operator_choice_required",
                historical=duplicate["historical"][:5],
            )

        selection = self._project_process_selection()
        requested_process = str(process_id or "").strip()
        selected_process, selection_result = self._select_process(selection, requested_process)
        if not selected_process:
            return selection_result
        try:
            definition = self.core.resolve_process_definition(self.project_root, selected_process)
        except (OSError, SystemExit, ValueError):
            return self._blocked("process_definition_unavailable", process_id=selected_process)
        process = copy.deepcopy(definition.process)
        stages = executable_stages(process)
        if not stages:
            return self._blocked("process_has_no_executable_stages", process_id=selected_process)
        try:
            stage_id = initial_stage_id(process)
            if stage_override:
                valid = {str(item.get("id")) for item in stages}
                if stage_override not in valid:
                    return self._blocked(
                        "invalid_preferred_stage",
                        action="operator_choice_required",
                        valid_stages=sorted(valid),
                    )
                stage_id = stage_override
            for stage in stages:
                normalized_outcomes(process, str(stage.get("id")))
        except ValueError as exc:
            return self._blocked("invalid_process_definition", message=str(exc), process_id=selected_process)

        now = self.core.now_utc()
        flow_root = self._flow_root()
        run_id = self._unique_id(flow_root / "runs", "garage-" + self.core.safe_id(objective, "work"))
        assignment_id = self._unique_id(flow_root / "assignments", self.core.safe_id(objective, "task"))
        specialization_selection = project_specialization_selection(self._manifest(), process)
        active_specializations = specialization_selection["active"]
        selected_resource_ids = self._selected_resource_ids()
        pin = self._process_pin(process, definition.path, active_specializations=active_specializations, selected_resource_ids=selected_resource_ids, allowed_processes=selection["allowed"])
        run = {
            "schema_version": 1,
            "id": run_id,
            "title": objective[:80],
            "process": selected_process,
            "status": "in_progress",
            "created_at": now,
            "updated_at": now,
            "objective": objective,
            "platform": "",
            "selected_specializations": active_specializations,
            "scope": {"type": "project", "project_root": "."},
            "tasks": [{"id": assignment_id, "assignment": f".pf/assignments/{assignment_id}.yaml", "status": "in_progress", "order": 1, "blocking": True}],
            "final_artifacts": [],
            "events": {"emitted": ["run.created", "process.stage.started"]},
            "privacy": {"public_safe": True},
            "process_execution": pin,
        }
        assignment = {
            "schema_version": 1,
            "id": assignment_id,
            "title": objective[:80],
            "run_id": run_id,
            "process": selected_process,
            "status": "in_progress",
            "created_at": now,
            "updated_at": now,
            "objective": objective,
            "platform": "",
            "selected_specializations": active_specializations,
            "order": 1,
            "dependencies": {"blocked_by": [], "blocks": []},
            "iterations": [],
            "result": {"status": "pending", "summary": "", "artifacts": []},
            "execution_mode": {"kind": "implementation", "code_changes_allowed": True, "artifact_changes_allowed": True, "requires_review": True},
            "stage": stage_id,
            "stage_status": "in_progress",
            "stage_execution": {"started_at": now, "evidence": [], "notes": ""},
            "stage_history": [],
            "process_execution": {
                "process_id": pin["process_id"],
                "process_version": pin["process_version"],
                "process_fingerprint": pin["process_fingerprint"],
                "snapshot_id": pin["snapshot_id"],
                "snapshot_checksum": pin["snapshot_checksum"],
            },
        }
        if session_id:
            assignment["session"] = {"status": "bound", "id": session_id}
        capsule_path, capsule_checksum = self._write_capsule(run, assignment, pin)
        run["process_execution"]["assignment_capsule"] = capsule_path
        run["process_execution"]["assignment_capsule_checksum"] = capsule_checksum
        assignment["process_execution"]["assignment_capsule"] = capsule_path
        assignment["process_execution"]["assignment_capsule_checksum"] = capsule_checksum

        run_path = self._run_path(run_id)
        assignment_path = self._assignment_path(assignment_id)
        self._atomic_yaml(run_path, run)
        self._atomic_yaml(assignment_path, assignment)
        self._atomic_text(run_path.parent / "plan.md", f"# Run Plan: {objective[:80]}\n\nObjective: {objective}\n")
        self._write_task_index(run)
        self._emit("run.created", run, assignment, stage_id, outcome="started")
        self._emit("task.created", run, assignment, stage_id, outcome="started")
        self._emit("assignment.created", run, assignment, stage_id, outcome="started")
        self._emit("process.stage.started", run, assignment, stage_id, outcome="started", previous_stage_id="", next_stage_id=stage_id)
        state = self.state(run_id=run_id, assignment_id=assignment_id, session_id=session_id)
        self._write_projection(state)
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
        }

    def state(self, *, run_id: str = "", assignment_id: str = "", session_id: str = "") -> dict[str, Any]:
        selected = self._select_work(run_id=run_id, assignment_id=assignment_id, session_id=session_id)
        if not selected:
            return {
                "schema_version": 1,
                "kind": "pf.work.state",
                "action": "start_recommended",
                "project": {"id": self.core.project_id(self.project_root)},
            }
        run, assignment = selected
        process, pin_status = self._effective_process(run)
        stage_id = str(assignment.get("stage") or "")
        stage = self._stage(process, stage_id)
        current_evidence = self._current_evidence(assignment)
        accumulated_evidence = self._accumulated_evidence(assignment)
        required_inputs = [
            self._requirement_state("input", str(item), accumulated_evidence)
            for item in self._string_list(stage.get("required_inputs"))
        ]
        required_artifact_ids = self._required_artifact_ids(process, stage)
        artifacts = [self._requirement_state("artifact", item, current_evidence) for item in required_artifact_ids]
        required_evidence = [
            self._requirement_state("evidence", item, current_evidence)
            for item in self._string_list(stage.get("required_evidence"))
        ]
        entry_gates = [
            self._gate_state(process, str(gate_id), accumulated_evidence, phase="entry")
            for gate_id in self._string_list(stage.get("entry_gates"))
        ]
        exit_gates = [
            self._gate_state(process, str(gate_id), current_evidence, phase="exit")
            for gate_id in self._string_list(stage.get("exit_gates"))
        ]
        obligations = self._automation_states(process, stage, assignment)
        incomplete = self._stage_requirements(required_inputs, artifacts, required_evidence, entry_gates + exit_gates, obligations)
        completion = stage.get("stage_completion") if isinstance(stage.get("stage_completion"), dict) else process.get("stage_completion") if isinstance(process.get("stage_completion"), dict) else {}
        if completion.get("evidence_required") is True and not current_evidence:
            incomplete.append({"code": "stage_evidence_required", "stage_id": stage_id})
        stage_execution = assignment.get("stage_execution") if isinstance(assignment.get("stage_execution"), dict) else {}
        if completion.get("handoff_note_required") is True and not str(stage_execution.get("notes") or "").strip():
            incomplete.append({"code": "handoff_note_required", "stage_id": stage_id})
        try:
            outcomes = normalized_outcomes(process, stage_id)
        except ValueError as exc:
            outcomes = []
            incomplete.append({"code": "invalid_process_definition", "message": str(exc), "stage_id": stage_id})
        stored_blockers = stage_execution.get("blockers") if isinstance(stage_execution.get("blockers"), list) else []
        blockers = [copy.deepcopy(item) for item in stored_blockers if isinstance(item, dict)]
        if str(assignment.get("stage_status") or "") == "blocked" and not blockers:
            blockers.append({"code": "stage_marked_blocked", "stage_id": stage_id})
        if str(run.get("status") or "") == "completed":
            action = "run_completed"
        elif blockers:
            action = "work_blocked"
        elif incomplete:
            action = "work_incomplete"
        else:
            action = "work_ready"
        return {
            "schema_version": 1,
            "kind": "pf.work.state",
            "action": action,
            "project": {"id": self.core.project_id(self.project_root)},
            "process": {
                "id": str(process.get("id") or run.get("process") or ""),
                "version": str(process.get("version") or ""),
                "fingerprint": str((run.get("process_execution") or {}).get("process_fingerprint") or canonical_fingerprint(process)),
                "pin_status": pin_status,
            },
            "work": {
                "active_specializations": _stable_ids(assignment.get("selected_specializations") or run.get("selected_specializations")),
                "selected_resource_ids": _stable_ids((run.get("process_execution") or {}).get("selected_resource_ids")),
            },
            "run": {"id": str(run.get("id") or ""), "status": str(run.get("status") or "")},
            "assignment": {"id": str(assignment.get("id") or ""), "status": str(assignment.get("status") or "")},
            "stage": {"id": stage_id, "title": str(stage.get("title") or stage_id), "status": str(assignment.get("stage_status") or "in_progress")},
            "required_inputs": required_inputs,
            "required_evidence": required_evidence,
            "obligations": obligations,
            "artifacts": artifacts,
            "gates": {"entry": entry_gates, "exit": exit_gates},
            "allowed_outcomes": outcomes,
            "blockers": blockers,
            "incomplete": incomplete,
            "completion": {"status": "complete" if not incomplete else "incomplete", "requirements": incomplete},
            "evidence": current_evidence,
        }

    def allowed_transitions(self, *, run_id: str = "", assignment_id: str = "", session_id: str = "") -> dict[str, Any]:
        state = self.state(run_id=run_id, assignment_id=assignment_id, session_id=session_id)
        return {
            "schema_version": 1,
            "kind": "pf.work.allowed_transitions",
            "run": state.get("run", {}),
            "assignment": state.get("assignment", {}),
            "stage": state.get("stage", {}),
            "allowed_outcomes": state.get("allowed_outcomes", []),
            "blockers": state.get("blockers", []),
        }

    def transition(
        self,
        *,
        outcome: str,
        evidence: Any = None,
        notes: str = "",
        run_id: str = "",
        assignment_id: str = "",
        session_id: str = "",
    ) -> dict[str, Any]:
        selected = self._select_work(run_id=run_id, assignment_id=assignment_id, session_id=session_id)
        if not selected:
            return self._blocked("active_work_not_found")
        run, assignment = selected
        if not isinstance(run.get("process_execution"), dict) or not isinstance(run["process_execution"].get("definition"), dict):
            return self._blocked("process_not_pinned", run_id=run.get("id"), assignment_id=assignment.get("id"))
        with self._run_lock(str(run.get("id") or "")):
            run = self._load_run(str(run.get("id") or ""))
            assignment = self._load_assignment(str(assignment.get("id") or ""))
            pending_intent, intent_error = self._load_completion_intent(run, assignment)
            if pending_intent is not None:
                return self._replay_completion_intent(pending_intent, session_id=session_id)
            if intent_error:
                return self._blocked(
                    "completion_intent_invalid",
                    run_id=run.get("id"),
                    assignment_id=assignment.get("id"),
                    detail=intent_error,
                )
            if str(run.get("status") or "") in TERMINAL_RUN_STATUSES or str(assignment.get("status") or "") in TERMINAL_ASSIGNMENT_STATUSES:
                return self._blocked("work_is_terminal", run_id=run.get("id"), assignment_id=assignment.get("id"), run_status=run.get("status"), assignment_status=assignment.get("status"))
            process, pin_status = self._effective_process(run)
            if pin_status != "pinned":
                return self._blocked("process_pin_invalid", run_id=run.get("id"), assignment_id=assignment.get("id"), pin_status=pin_status)
            stage_id = str(assignment.get("stage") or "")
            normalized_evidence, evidence_blockers = self._normalize_evidence(evidence)
            if evidence_blockers:
                return self._transition_rejected(
                    run=run,
                    assignment=assignment,
                    session_id=session_id,
                    reason="invalid_evidence",
                    blockers=evidence_blockers,
                )
            try:
                allowed_outcomes = {str(item.get("id")): item for item in normalized_outcomes(process, stage_id) if isinstance(item, dict)}
            except ValueError as exc:
                return self._transition_rejected(
                    run=run,
                    assignment=assignment,
                    session_id=session_id,
                    reason="invalid_process_definition",
                    blockers=[{"code": "invalid_process_definition", "message": str(exc), "stage_id": stage_id}],
                )
            if outcome not in allowed_outcomes:
                return self._transition_rejected(
                    run=run,
                    assignment=assignment,
                    session_id=session_id,
                    reason="outcome_not_allowed",
                    blockers=[{"code": "outcome_not_allowed", "outcome": outcome, "allowed": sorted(allowed_outcomes)}],
                )
            stage_execution = assignment.get("stage_execution") if isinstance(assignment.get("stage_execution"), dict) else {}
            stored_blockers = stage_execution.get("blockers") if isinstance(stage_execution.get("blockers"), list) else []
            if stored_blockers:
                if not all(self._is_recoverable_transition_rejection(item) for item in stored_blockers if isinstance(item, dict)):
                    return self.state(run_id=str(run.get("id") or ""), assignment_id=str(assignment.get("id") or ""), session_id=session_id)
                # Older releases persisted request-validation failures as a
                # stage block. A valid retry is the recovery operation; do not
                # require users to repair assignment YAML by hand.
                stage_execution.pop("blockers", None)
                stage_execution.pop("blocked_at", None)
                if str(assignment.get("stage_status") or "") == "blocked":
                    assignment["stage_status"] = "in_progress"
            stage_execution = {**stage_execution, "evidence": self._merge_evidence(stage_execution.get("evidence"), normalized_evidence), "notes": str(notes or stage_execution.get("notes") or "")}
            assignment["stage_execution"] = stage_execution
            assignment["updated_at"] = self.core.now_utc()
            self._atomic_yaml(self._assignment_path(str(assignment["id"])), assignment)
            preview = self.state(run_id=str(run.get("id") or ""), assignment_id=str(assignment.get("id") or ""), session_id=session_id)
            preview_blockers = list(preview.get("blockers") or [])
            preview_incomplete = list(preview.get("incomplete") or [])
            outcomes = {str(item.get("id")): item for item in preview.get("allowed_outcomes", []) if isinstance(item, dict)}
            next_stage_id = str(outcomes.get(outcome, {}).get("next_stage") or "")
            if next_stage_id:
                next_stage = self._stage(process, next_stage_id)
                accumulated = self._accumulated_evidence(assignment)
                for gate_id in self._string_list(next_stage.get("entry_gates")):
                    gate = self._gate_state(process, gate_id, accumulated, phase="entry")
                    if not gate["satisfied"] and gate.get("blocking", True):
                        preview_incomplete.append({"code": "entry_gate_evidence_missing", "gate_id": gate_id, "stage_id": next_stage_id})
            if preview_blockers:
                return self._transition_rejected(
                    run=run,
                    assignment=assignment,
                    session_id=session_id,
                    reason="stage_transition_rejected",
                    blockers=preview_blockers,
                )

            if preview_incomplete:
                incomplete_state = self.state(run_id=str(run["id"]), assignment_id=str(assignment["id"]), session_id=session_id)
                self._write_projection(incomplete_state)
                return {**incomplete_state, "action": "incomplete", "reason": "stage_requirements_incomplete", "incomplete": preview_incomplete}

            if not next_stage_id:
                completion_blockers = self._run_completion_blockers(process, run, assignment)
                if completion_blockers:
                    incomplete_state = self.state(run_id=str(run["id"]), assignment_id=str(assignment["id"]), session_id=session_id)
                    self._write_projection(incomplete_state)
                    return {**incomplete_state, "action": "incomplete", "reason": "run_completion_incomplete", "incomplete": completion_blockers}

            now = self.core.now_utc()
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
                self._set_run_task_status(run, str(assignment["id"]), "in_progress")
                self._atomic_yaml(self._assignment_path(str(assignment["id"])), assignment)
                self._atomic_yaml(self._run_path(str(run["id"])), run)
                self._write_task_index(run)
                action = "stage_transitioned"
            else:
                intent = self._build_completion_intent(
                    run,
                    assignment,
                    process,
                    outcome=outcome,
                    notes=notes,
                    completed_at=now,
                )
                # JSON is valid YAML and preserves multiline payloads exactly;
                # the generic YAML formatter folds quoted multiline strings.
                self._atomic_text(self._completion_intent_path(str(run["id"])), json.dumps(intent, ensure_ascii=False, sort_keys=True, indent=2) + "\n")
                self._replay_completion_intent(intent, session_id=session_id)
                action = "run_completed"

            result_state = self.state(run_id=str(run["id"]), assignment_id=str(assignment["id"]), session_id=session_id)
            if action != "run_completed":
                self._write_projection(result_state)
                self._emit("process.stage.completed", run, assignment, previous_stage_id, outcome=outcome, previous_stage_id=previous_stage_id, next_stage_id=next_stage_id)
                self._emit("process.stage.transitioned", run, assignment, next_stage_id or previous_stage_id, outcome=outcome, previous_stage_id=previous_stage_id, next_stage_id=next_stage_id)
                if next_stage_id:
                    self._emit("process.stage.started", run, assignment, next_stage_id, outcome="started", previous_stage_id=previous_stage_id, next_stage_id=next_stage_id)
            result = {**result_state, "action": action, "previous_stage_id": previous_stage_id, "next_stage_id": next_stage_id}
            if action == "run_completed":
                result.update(self._next_work_advisory(process, run))
            return result

    def can_complete(self, *, run_id: str = "", assignment_id: str = "", session_id: str = "") -> dict[str, Any]:
        selected = self._select_work(run_id=run_id, assignment_id=assignment_id, session_id=session_id)
        if not selected:
            return {"can_complete": False, "blockers": [{"code": "active_work_not_found"}]}
        run, assignment = selected
        process, pin_status = self._effective_process(run)
        stage_id = str(assignment.get("stage") or "")
        outcomes = normalized_outcomes(process, stage_id)
        final = any(not str(item.get("next_stage") or "") for item in outcomes)
        state = self.state(run_id=str(run.get("id") or ""), assignment_id=str(assignment.get("id") or ""), session_id=session_id)
        blockers = [*list(state.get("blockers") or []), *list(state.get("incomplete") or [])]
        if pin_status != "pinned":
            blockers.append({"code": "process_not_pinned"})
        if not final:
            blockers.append({"code": "not_final_stage", "stage_id": stage_id})
        blockers.extend(self._run_completion_blockers(process, run, assignment))
        return {"can_complete": not blockers, "blockers": blockers, "run": state.get("run"), "assignment": state.get("assignment"), "stage": state.get("stage")}

    def complete(self, *, outcome: str = "completed", evidence: Any = None, notes: str = "", run_id: str = "", assignment_id: str = "", session_id: str = "") -> dict[str, Any]:
        selected = self._select_work(run_id=run_id, assignment_id=assignment_id, session_id=session_id)
        if selected:
            run, assignment = selected
            pending, _error = self._load_completion_intent(run, assignment)
            if pending is not None:
                # A committed intent is authoritative.  Do not make a retry
                # depend on mutable evidence or on the caller repeating the
                # original outcome/notes.
                return self.transition(
                    outcome=outcome,
                    evidence=evidence,
                    notes=notes,
                    run_id=run_id,
                    assignment_id=assignment_id,
                    session_id=session_id,
                )
        readiness = self.can_complete(run_id=run_id, assignment_id=assignment_id, session_id=session_id)
        if readiness["blockers"] and not evidence:
            return {"schema_version": 1, "kind": "pf.work.complete", "action": "blocked", **readiness}
        return self.transition(outcome=outcome, evidence=evidence, notes=notes, run_id=run_id, assignment_id=assignment_id, session_id=session_id)

    def _context_check(self) -> dict[str, Any]:
        explicit = ""
        if self.workplace_root and (self.workplace_root / "workplace.yaml").is_file():
            explicit = str(self.workplace_root)
        return self.core.project_context_check_result(self.project_root, explicit_workplace=explicit or None)

    def _manifest(self) -> dict[str, Any]:
        return self.core.load_yaml_document(self._flow_root() / "process-forge.yaml")

    def _project_process_selection(self) -> dict[str, Any]:
        return project_process_selection(self._manifest())

    def _select_process(self, selection: dict[str, Any], requested: str) -> tuple[str, dict[str, Any]]:
        allowed = _stable_ids(selection.get("allowed"))
        if requested:
            if requested not in allowed:
                try:
                    self.core.resolve_process_definition(self.project_root, requested)
                except (OSError, SystemExit, ValueError):
                    return "", self._blocked("process_not_found", process_id=requested)
                return "", self._blocked("process_not_allowed", process_id=requested, allowed_processes=allowed)
            return requested, {}
        if len(allowed) == 1:
            return allowed[0], {}
        default = str(selection.get("default") or "").strip()
        return "", self._blocked(
            "process_choice_required",
            action="process_choice_required",
            default_process=default if default in allowed else "",
            candidates=self._process_candidates(allowed, default=default),
        )

    def _process_candidates(self, process_ids: list[str], *, default: str = "") -> list[dict[str, Any]]:
        candidates: list[dict[str, Any]] = []
        for process_id in process_ids:
            try:
                process = self.core.resolve_process_definition(self.project_root, process_id).process
            except (OSError, SystemExit, ValueError):
                candidates.append({"id": process_id, "title": process_id, "purpose": "Process definition unavailable.", "expected_result": "", "default": process_id == default})
                continue
            candidates.append(
                {
                    "id": str(process.get("id") or process_id),
                    "title": str(process.get("name") or process_id),
                    "purpose": str(process.get("purpose") or process.get("description") or ""),
                    "expected_result": str(process.get("expected_result") or ""),
                    "default": str(process.get("id") or process_id) == default,
                }
            )
        return candidates

    @staticmethod
    def _is_recoverable_transition_rejection(blocker: Any) -> bool:
        if not isinstance(blocker, dict):
            return False
        return str(blocker.get("code") or "") in {
            "invalid_evidence",
            "not_applicable_evidence_incomplete",
            "artifact_path_missing",
            "outcome_not_allowed",
            "invalid_process_definition",
        }

    def _transition_rejected(self, *, run: dict[str, Any], assignment: dict[str, Any], session_id: str, reason: str, blockers: list[dict[str, Any]]) -> dict[str, Any]:
        state = self.state(run_id=str(run.get("id") or ""), assignment_id=str(assignment.get("id") or ""), session_id=session_id)
        return {**state, "action": "transition_rejected", "reason": reason, "blockers": blockers}

    def _process_pin(self, process: dict[str, Any], source_path: Path, *, active_specializations: list[str], selected_resource_ids: list[str], allowed_processes: list[str]) -> dict[str, Any]:
        snapshot_path = self._flow_root() / "contexts" / "project-context.snapshot.yaml"
        snapshot = self.core.load_yaml_document(snapshot_path)
        meta = snapshot.get("snapshot") if isinstance(snapshot.get("snapshot"), dict) else {}
        snapshot_checksum = "sha256:" + self._sha256_file(snapshot_path) if snapshot_path.is_file() else ""
        normalized = json.loads(json.dumps(process, ensure_ascii=False))
        try:
            process_source = source_path.resolve().relative_to(self.project_root.resolve()).as_posix()
        except ValueError:
            process_source = f"catalog:{normalized.get('id') or source_path.stem}"
        return {
            "process_id": str(normalized.get("id") or ""),
            "process_version": str(normalized.get("version") or ""),
            "process_fingerprint": canonical_fingerprint(normalized),
            "process_source": process_source,
            "snapshot_id": str(meta.get("id") or ""),
            "snapshot_checksum": snapshot_checksum,
            "definition": normalized,
            "active_specializations": active_specializations,
            "selected_resource_ids": selected_resource_ids,
            "allowed_processes": allowed_processes,
        }

    def _selected_resource_ids(self) -> list[str]:
        snapshot = self.core.load_yaml_document(self._flow_root() / "contexts" / "project-context.snapshot.yaml")
        resolved = snapshot.get("resolved") if isinstance(snapshot.get("resolved"), dict) else {}
        return _stable_ids(resolved.get("knowledge_resources"))

    def _next_work_advisory(self, process: dict[str, Any], run: dict[str, Any]) -> dict[str, Any]:
        pin = run.get("process_execution") if isinstance(run.get("process_execution"), dict) else {}
        current = str(run.get("process") or "")
        available = [item for item in _stable_ids(pin.get("allowed_processes")) if item != current]
        declared = process.get("process_transitions") if isinstance(process.get("process_transitions"), list) else []
        routed = [str(item.get("to_process") or item.get("target_process") or "") for item in declared if isinstance(item, dict)]
        route_path = self._flow_root() / "process-routes.yaml"
        routes = self.core.load_yaml_document(route_path).get("routes", []) if route_path.exists() else []
        routed.extend(
            str(item.get("to_process") or item.get("target_process") or "")
            for item in routes
            if isinstance(item, dict) and str(item.get("from_process") or "") == current
        )
        recommended = next((item for item in routed if item in available), "")
        next_work: dict[str, Any] = {"available_processes": available}
        if recommended:
            next_work["recommended_process"] = recommended
        result: dict[str, Any] = {"next": next_work, "session_continuity": {"recommendation": "auto", "reason": "process_boundary"}}
        handoff = next((str(path) for path in _stable_ids(run.get("final_artifacts")) if path.endswith("-handoff.md")), "")
        if handoff:
            result["handoff"] = {"path": handoff}
        return result

    def _effective_process(self, run: dict[str, Any]) -> tuple[dict[str, Any], str]:
        pin = run.get("process_execution") if isinstance(run.get("process_execution"), dict) else {}
        definition = pin.get("definition") if isinstance(pin.get("definition"), dict) else None
        if definition is not None and str(pin.get("process_fingerprint") or "") == canonical_fingerprint(definition):
            return copy.deepcopy(definition), "pinned"
        if pin:
            return copy.deepcopy(definition) if isinstance(definition, dict) else {"id": str(run.get("process") or ""), "stages": []}, "corrupt"
        try:
            resolved = self.core.resolve_process_definition(self.project_root, str(run.get("process") or ""))
            return copy.deepcopy(resolved.process), "legacy_unpinned"
        except (OSError, SystemExit, ValueError):
            return {"id": str(run.get("process") or ""), "stages": []}, "missing"

    def _stage(self, process: dict[str, Any], stage_id: str) -> dict[str, Any]:
        return next((stage for stage in executable_stages(process) if str(stage.get("id")) == stage_id), {"id": stage_id})

    def _select_work(self, *, run_id: str = "", assignment_id: str = "", session_id: str = "") -> tuple[dict[str, Any], dict[str, Any]] | None:
        records = self._work_records(include_historical=True)
        if assignment_id:
            record = next((item for item in records if item["assignment_id"] == assignment_id), None)
        elif run_id:
            candidates = [item for item in records if item["run_id"] == run_id]
            record = self._preferred_record(candidates, session_id)
        else:
            active = [item for item in records if item["active"]]
            record = self._preferred_record(active, session_id)
        if not record:
            return None
        return self._load_run(record["run_id"]), self._load_assignment(record["assignment_id"])

    def _preferred_record(self, records: list[dict[str, Any]], session_id: str) -> dict[str, Any] | None:
        if session_id:
            bound = [item for item in records if item.get("session_id") == session_id]
            if bound:
                records = bound
        return max(records, key=lambda item: (item.get("updated_at", ""), item.get("created_at", ""), item.get("assignment_id", ""))) if records else None

    def _work_records(self, *, include_historical: bool) -> list[dict[str, Any]]:
        records: list[dict[str, Any]] = []
        runs_root = self._flow_root() / "runs"
        for path in sorted(runs_root.glob("*/run.yaml")) if runs_root.is_dir() else []:
            run = self.core.load_yaml_document(path)
            run_id = str(run.get("id") or path.parent.name)
            if not SAFE_ID_RE.fullmatch(run_id):
                continue
            for entry in run.get("tasks", []) if isinstance(run.get("tasks"), list) else []:
                if not isinstance(entry, dict) or not entry.get("id"):
                    continue
                entry_id = str(entry["id"])
                if not SAFE_ID_RE.fullmatch(entry_id):
                    continue
                task = self.core.load_yaml_document(self._assignment_path(entry_id))
                if not task:
                    continue
                task_id = str(task.get("id") or entry_id)
                if not SAFE_ID_RE.fullmatch(task_id) or str(task.get("run_id") or run_id) != run_id:
                    continue
                status = str(task.get("status") or entry.get("status") or "")
                pending_completion, _intent_error = self._load_completion_intent(run, task)
                has_pending_completion = pending_completion is not None
                active = has_pending_completion or (status in ACTIVE_ASSIGNMENT_STATUSES and str(run.get("status") or "") in ACTIVE_RUN_STATUSES)
                if not active and not include_historical:
                    continue
                session = task.get("session") if isinstance(task.get("session"), dict) else {}
                records.append(
                    {
                        "run_id": run_id,
                        "assignment_id": task_id,
                        "objective": str(task.get("objective") or run.get("objective") or ""),
                        "status": status,
                        "run_status": str(run.get("status") or ""),
                        "stage": str(task.get("stage") or ""),
                        "active": active,
                        "session_id": str(session.get("id") or ""),
                        "created_at": str(task.get("created_at") or run.get("created_at") or ""),
                        "updated_at": str(task.get("updated_at") or run.get("updated_at") or ""),
                        "pending_completion": has_pending_completion,
                    }
                )
        return records

    def _find_by_objective(self, objective: str) -> dict[str, Any]:
        normalized = " ".join(objective.casefold().split())
        matches = [item for item in self._work_records(include_historical=True) if " ".join(item["objective"].casefold().split()) == normalized]
        active = self._preferred_record([item for item in matches if item["active"]], "")
        historical = [item for item in matches if not item["active"]]
        return {"active": active, "historical": historical}

    def _current_evidence(self, assignment: dict[str, Any]) -> list[dict[str, Any]]:
        execution = assignment.get("stage_execution") if isinstance(assignment.get("stage_execution"), dict) else {}
        return [copy.deepcopy(item) for item in execution.get("evidence", []) if isinstance(item, dict)] if isinstance(execution.get("evidence"), list) else []

    def _accumulated_evidence(self, assignment: dict[str, Any]) -> list[dict[str, Any]]:
        evidence: list[dict[str, Any]] = []
        history = assignment.get("stage_history") if isinstance(assignment.get("stage_history"), list) else []
        for record in history:
            if isinstance(record, dict) and isinstance(record.get("evidence"), list):
                evidence.extend(copy.deepcopy(item) for item in record["evidence"] if isinstance(item, dict))
        evidence.extend(self._current_evidence(assignment))
        return evidence

    def _required_artifact_ids(self, process: dict[str, Any], stage: dict[str, Any]) -> list[str]:
        declared = self._string_list(stage.get("required_artifacts"))
        if declared:
            return declared
        definitions = process.get("artifact_definitions") if isinstance(process.get("artifact_definitions"), list) else []
        optional = {str(item.get("id")) for item in definitions if isinstance(item, dict) and item.get("required") is False}
        consumed_inputs = {
            artifact_id
            for candidate in executable_stages(process)
            for artifact_id in self._string_list(candidate.get("required_inputs"))
        }
        return [item for item in self._string_list(stage.get("produced_artifacts")) if item not in optional or item in consumed_inputs]

    def _requirement_state(self, kind: str, identifier: str, evidence: list[dict[str, Any]]) -> dict[str, Any]:
        aliases = {"artifact": ("artifact_id", "id"), "input": ("input_id", "artifact_id", "id"), "evidence": ("evidence_id", "id")}
        accepted_kinds = {"artifact": {"artifact"}, "input": {"input", "artifact"}, "evidence": {"evidence", "attestation"}}
        statuses = {"ready", "present", "passed", "approved", "not_applicable"}
        match = next(
            (
                item
                for item in reversed(evidence)
                if str(item.get("kind") or "") in accepted_kinds[kind]
                and any(str(item.get(key) or "") == identifier for key in aliases[kind])
            ),
            None,
        )
        if match is None:
            return {"id": identifier, "kind": kind, "satisfied": False, "evidence": {}}
        diagnostic = self._evidence_file_diagnostic(match)
        status = str(match.get("status") or "")
        if diagnostic is None and status not in statuses:
            diagnostic = {"code": "evidence_status_not_acceptable", "status": status or "missing", "id": identifier}
        result = {"id": identifier, "kind": kind, "satisfied": diagnostic is None, "evidence": copy.deepcopy(match)}
        if diagnostic is not None:
            result["diagnostic"] = diagnostic
        return result

    def _gate_state(self, process: dict[str, Any], gate_id: str, evidence: list[dict[str, Any]], *, phase: str) -> dict[str, Any]:
        definitions = process.get("gates") if isinstance(process.get("gates"), list) else []
        definition = next((item for item in definitions if isinstance(item, dict) and str(item.get("id") or "") == gate_id), {})
        match = next(
            (
                item
                for item in reversed(evidence)
                if str(item.get("kind") or "") == "gate"
                and str(item.get("gate_id") or item.get("id") or "") == gate_id
            ),
            None,
        )
        diagnostic = self._evidence_file_diagnostic(match) if match is not None else None
        if diagnostic is None and match is not None and str(match.get("status") or "") not in {"passed", "approved", "not_applicable"}:
            diagnostic = {"code": "evidence_status_not_acceptable", "status": str(match.get("status") or "missing"), "id": gate_id}
        result = {
            "id": gate_id,
            "phase": phase,
            "type": str(definition.get("type") or "checklist"),
            "blocking": bool(definition.get("blocking", True)),
            "required": bool(definition.get("required", True)),
            "satisfied": match is not None and diagnostic is None,
            "evidence": copy.deepcopy(match) if match is not None else {},
        }
        if diagnostic is not None:
            result["diagnostic"] = diagnostic
        return result

    def _automation_states(self, process: dict[str, Any], stage: dict[str, Any], assignment: dict[str, Any]) -> list[dict[str, Any]]:
        bindings = stage.get("automation_bindings") if isinstance(stage.get("automation_bindings"), list) else []
        if not bindings and isinstance(stage.get("technical_obligations"), list):
            bindings = stage["technical_obligations"]
        states: list[dict[str, Any]] = []
        for binding in bindings:
            if not isinstance(binding, dict):
                continue
            projector = str(binding.get("projector") or "")
            status = "unsupported"
            details: dict[str, Any] = {}
            if projector == "required-output-readiness" and hasattr(self.core, "required_output_checks"):
                failures = [item.message for item in self.core.required_output_checks(self.project_root, assignment) if str(getattr(item, "level", "")) == "FAIL"]
                status = "ready" if not failures else "blocked"
                details["failures"] = failures
            elif projector == "verification-state":
                verification = binding.get("verification") if isinstance(binding.get("verification"), dict) else {}
                passed_event = str(verification.get("passed_event") or "")
                failed_event = str(verification.get("failed_event") or "")
                event = self._latest_assignment_event(str(assignment.get("id") or ""), {passed_event, failed_event})
                event_type = str(event.get("event_type") or "") if event else ""
                status = "ready" if event_type == passed_event else ("blocked" if event_type == failed_event else "missing")
                if status == "ready" and hasattr(self.core, "task_verification_fingerprint"):
                    event_data = event.get("data") if isinstance(event.get("data"), dict) else {}
                    if str(event_data.get("verification_fingerprint") or "") != self.core.task_verification_fingerprint(self.project_root, assignment):
                        status = "stale"
                details["event_type"] = event_type
            states.append({"id": str(binding.get("id") or projector or "obligation"), "projector": projector, "gate": str(binding.get("gate") or ""), "status": status, **details})
        return states

    def _stage_requirements(self, inputs: list[dict[str, Any]], artifacts: list[dict[str, Any]], required_evidence: list[dict[str, Any]], gates: list[dict[str, Any]], obligations: list[dict[str, Any]]) -> list[dict[str, Any]]:
        requirements: list[dict[str, Any]] = []
        requirements.extend(self._requirement_blocker("required_input_missing", "input_id", item) for item in inputs if not item["satisfied"])
        requirements.extend(self._requirement_blocker("artifact_evidence_missing", "artifact_id", item) for item in artifacts if not item["satisfied"])
        requirements.extend(self._requirement_blocker("required_evidence_missing", "evidence_id", item) for item in required_evidence if not item["satisfied"])
        requirements.extend(self._requirement_blocker("gate_evidence_missing", "gate_id", item) for item in gates if item["required"] and item["blocking"] and not item["satisfied"])
        requirements.extend({"code": "automation_not_ready", "obligation_id": item["id"], "status": item["status"]} for item in obligations if item["status"] != "ready")
        return requirements

    def _requirement_blocker(self, code: str, identifier_key: str, requirement: dict[str, Any]) -> dict[str, Any]:
        blocker = {"code": code, identifier_key: requirement["id"]}
        diagnostic = requirement.get("diagnostic")
        if isinstance(diagnostic, dict):
            blocker["diagnostic"] = copy.deepcopy(diagnostic)
        return blocker

    def _normalize_evidence(self, evidence: Any) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        values = evidence if isinstance(evidence, list) else ([] if evidence is None or evidence == "" else [evidence])
        normalized: list[dict[str, Any]] = []
        blockers: list[dict[str, Any]] = []
        now = self.core.now_utc()
        for index, value in enumerate(values):
            if isinstance(value, str):
                item = {"kind": "attestation", "id": f"attestation-{index + 1}", "status": "ready", "summary": value}
            elif isinstance(value, dict):
                item = copy.deepcopy(value)
            else:
                blockers.append({"code": "invalid_evidence", "index": index})
                continue
            item.setdefault("kind", "attestation")
            item.setdefault("status", "ready")
            item["recorded_at"] = now
            if str(item.get("status") or "") == "not_applicable":
                reason = str(item.get("reason") or "").strip()
                supporting = item.get("evidence")
                if not reason or not isinstance(supporting, list) or not supporting:
                    blockers.append({"code": "not_applicable_evidence_incomplete", "index": index})
                    continue
            path_value = str(item.get("path") or "").strip()
            if path_value:
                safe_path = self._safe_evidence_path(path_value)
                try:
                    valid_file = safe_path is not None and safe_path.is_file()
                except OSError:
                    valid_file = False
                if not valid_file:
                    blockers.append({"code": "artifact_path_missing", "index": index, "path": path_value})
                    continue
                else:
                    try:
                        item["path"] = self.core.rel(safe_path, self.project_root)
                        item["sha256"] = "sha256:" + self._sha256_file(safe_path)
                    except OSError:
                        blockers.append({"code": "artifact_path_unreadable", "index": index, "path": path_value})
                        continue
            normalized.append(item)
        return normalized, blockers

    def _safe_evidence_path(self, value: str) -> Path | None:
        try:
            path = Path(value)
            if path.is_absolute():
                return None
            resolved = (self.project_root / path).resolve()
        except (OSError, RuntimeError, ValueError):
            return None
        try:
            resolved.relative_to(self.project_root.resolve())
        except (OSError, RuntimeError, ValueError):
            return None
        return resolved

    def _merge_evidence(self, existing: Any, incoming: list[dict[str, Any]]) -> list[dict[str, Any]]:
        values = [copy.deepcopy(item) for item in existing if isinstance(item, dict)] if isinstance(existing, list) else []
        for item in incoming:
            marker = self._evidence_merge_identity(item)
            values = [current for current in values if self._evidence_merge_identity(current) != marker]
            values.append(item)
        return values

    def _evidence_merge_identity(self, item: dict[str, Any]) -> tuple[str, str]:
        kind = str(item.get("kind") or "")
        if kind == "gate":
            return ("gate", str(item.get("gate_id") or item.get("id") or ""))
        if kind in {"input", "artifact"}:
            # Inputs deliberately accept artifact-shaped evidence. Treat both
            # forms as one identity so a later alias cannot resurrect an older
            # positive record.
            return ("input_or_artifact", str(item.get("input_id") or item.get("artifact_id") or item.get("id") or ""))
        if kind in {"evidence", "attestation"}:
            return ("evidence", str(item.get("evidence_id") or item.get("id") or ""))
        return (kind, str(item.get("id") or ""))

    def _evidence_file_diagnostic(self, evidence: dict[str, Any] | None) -> dict[str, Any] | None:
        if not isinstance(evidence, dict):
            return None
        path_value = str(evidence.get("path") or "").strip()
        if not path_value:
            return None
        safe_path = self._safe_evidence_path(path_value)
        if safe_path is None:
            return {"code": "evidence_file_unsafe", "path": path_value}
        try:
            if not safe_path.exists():
                return {"code": "evidence_file_missing", "path": path_value}
            if not safe_path.is_file():
                return {"code": "evidence_file_not_regular", "path": path_value}
        except OSError as exc:
            return {"code": "evidence_file_unreadable", "path": path_value, "error": str(exc)}
        stored = str(evidence.get("sha256") or "").strip()
        if not stored:
            return {"code": "evidence_digest_missing", "path": path_value}
        try:
            actual = "sha256:" + self._sha256_file(safe_path)
        except OSError as exc:
            return {"code": "evidence_file_unreadable", "path": path_value, "error": str(exc)}
        if stored.casefold() != actual.casefold():
            return {"code": "evidence_file_changed", "path": path_value, "stored_sha256": stored, "actual_sha256": actual}
        return None

    def _latest_assignment_event(self, assignment_id: str, event_types: set[str]) -> dict[str, Any] | None:
        if not event_types or not hasattr(self.core, "event_runtime_paths"):
            return None
        events_path, _outbox = self.core.event_runtime_paths(self.project_root)
        if not events_path.is_file():
            return None
        for line in reversed(events_path.read_text(encoding="utf-8", errors="replace").splitlines()):
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue
            assignment = event.get("assignment") if isinstance(event.get("assignment"), dict) else {}
            if str(event.get("event_type") or "") in event_types and (str(assignment.get("id") or "") == assignment_id or str(event.get("subject") or "") == assignment_id):
                return event
        return None

    def _run_completion_blockers(self, process: dict[str, Any], run: dict[str, Any], assignment: dict[str, Any]) -> list[dict[str, Any]]:
        completion = process.get("run_completion") if isinstance(process.get("run_completion"), dict) else {}
        evidence = self._accumulated_evidence(assignment)
        blockers: list[dict[str, Any]] = []
        for gate_id in self._string_list(completion.get("gates")):
            gate = self._gate_state(process, gate_id, evidence, phase="run_completion")
            if gate["required"] and gate["blocking"] and not gate["satisfied"]:
                blocker = {"code": "run_completion_gate_missing", "gate_id": gate_id}
                if isinstance(gate.get("diagnostic"), dict):
                    blocker["diagnostic"] = copy.deepcopy(gate["diagnostic"])
                blockers.append(blocker)
        assignment_id = str(assignment.get("id") or "")
        for task in run.get("tasks", []) if isinstance(run.get("tasks"), list) else []:
            if not isinstance(task, dict) or str(task.get("id") or "") == assignment_id or task.get("blocking", True) is False:
                continue
            if str(task.get("status") or "") not in {"done", "completed", "cancelled"}:
                blockers.append({"code": "blocking_assignment_incomplete", "assignment_id": str(task.get("id") or ""), "status": str(task.get("status") or "")})
        return blockers

    def _completion_intent_path(self, run_id: str) -> Path:
        return self._run_path(run_id).parent / "completion-intent.yaml"

    def _build_completion_intent(
        self,
        run: dict[str, Any],
        assignment: dict[str, Any],
        process: dict[str, Any],
        *,
        outcome: str,
        notes: str,
        completed_at: str,
    ) -> dict[str, Any]:
        """Build every terminal payload before the first terminal write.

        The journal is deliberately self-contained.  A retry therefore does
        not re-run evidence selection, call ``now_utc`` again, or infer a new
        outcome from partially written records.
        """
        run_id = str(run["id"])
        assignment_id = str(assignment["id"])
        final_assignment = copy.deepcopy(assignment)
        final_assignment["stage_status"] = "completed"
        final_assignment["status"] = "done"
        final_assignment["updated_at"] = completed_at
        artifacts = [
            str(item.get("path"))
            for item in self._accumulated_evidence(final_assignment)
            if isinstance(item, dict) and item.get("path")
        ]
        final_assignment["result"] = {
            "status": "done",
            "summary": str(notes or f"Completed declarative process with outcome {outcome}."),
            "artifacts": sorted(set(artifacts)),
        }

        final_run = copy.deepcopy(run)
        self._set_run_task_status(final_run, assignment_id, "done")
        final_run["status"] = "completed"
        final_run["updated_at"] = completed_at
        summary_path = self._run_path(run_id).parent / "summary.md"
        handoff_path = self._flow_root() / "handoffs" / "runs" / f"{run_id}-handoff.md"
        task_index_path = self._run_path(run_id).parent / "task-index.md"
        projection_path = self._flow_root() / "artifacts" / "projections" / "process-execution-state.json"
        summary = self._render_summary(final_run, final_assignment)
        handoff = f"# Run Handoff: {run_id}\n\nStatus: `completed`\n\nSummary: `{self.core.rel(summary_path, self.project_root)}`\n"
        final_run["final_artifacts"] = [self.core.rel(summary_path, self.project_root), self.core.rel(handoff_path, self.project_root)]
        emitted = final_run.setdefault("events", {}).setdefault("emitted", []) if isinstance(final_run.setdefault("events", {}), dict) else []
        for event_type in ["process.stage.completed", "process.stage.transitioned", "task.completed", "assignment.completed", "run.completed", "run.summary.created"]:
            if isinstance(emitted, list) and event_type not in emitted:
                emitted.append(event_type)
        if hasattr(self.core, "render_task_index"):
            task_index = self.core.render_task_index(self.project_root, final_run)
        else:
            lines = [f"# Task Index: {run_id}", ""]
            lines.extend(f"- `{item.get('id')}`: `{item.get('status')}`" for item in final_run.get("tasks", []) if isinstance(item, dict))
            task_index = "\n".join(lines) + "\n"

        stage_id = str(assignment.get("stage") or "")
        intent_seed = f"{run_id}:{assignment_id}:{completed_at}:{outcome}"
        intent_id = "completion-" + hashlib.sha256(intent_seed.encode("utf-8")).hexdigest()[:32]
        event_specs = []
        for event_type, event_stage in [
            ("process.stage.completed", stage_id),
            ("process.stage.transitioned", stage_id),
            ("task.completed", stage_id),
            ("assignment.completed", stage_id),
            ("run.completed", stage_id),
            ("run.summary.created", stage_id),
        ]:
            event_specs.append(
                {
                    "event_type": event_type,
                    "event_id": "evt_" + hashlib.sha256(f"{intent_id}:{event_type}".encode("utf-8")).hexdigest()[:32],
                    "stage_id": event_stage,
                    "previous_stage_id": stage_id,
                    "next_stage_id": "",
                    "outcome": outcome,
                }
            )
        pin = final_run.get("process_execution") if isinstance(final_run.get("process_execution"), dict) else {}
        expected_run_path = self.core.rel(self._run_path(run_id), self.project_root)
        expected_assignment_path = self.core.rel(self._assignment_path(assignment_id), self.project_root)
        expected_journal_path = self.core.rel(self._completion_intent_path(run_id), self.project_root)
        intent = {
            "schema_version": 1,
            "kind": "pf.process.completion-intent",
            "intent_id": intent_id,
            "created_at": completed_at,
            "completed_at": completed_at,
            "run_id": run_id,
            "assignment_id": assignment_id,
            "journal_path": expected_journal_path,
            "owner": {
                "project_id": self.core.project_id(self.project_root),
                "run_path": expected_run_path,
                "assignment_path": expected_assignment_path,
            },
            "process_execution": copy.deepcopy(pin),
            "final": {
                "run": final_run,
                "assignment": final_assignment,
                "summary": {"path": self.core.rel(summary_path, self.project_root), "content": summary},
                "handoff": {"path": self.core.rel(handoff_path, self.project_root), "content": handoff},
                "task_index": {"path": self.core.rel(task_index_path, self.project_root), "content": task_index},
                "projection": {"path": self.core.rel(projection_path, self.project_root)},
                "events": event_specs,
            },
        }
        intent["fingerprint"] = canonical_fingerprint(intent)
        return intent

    def _load_completion_intent(self, run: dict[str, Any], assignment: dict[str, Any]) -> tuple[dict[str, Any] | None, str | None]:
        run_id = str(run.get("id") or "")
        assignment_id = str(assignment.get("id") or "")
        if not SAFE_ID_RE.fullmatch(run_id) or not SAFE_ID_RE.fullmatch(assignment_id):
            return None, None
        path = self._completion_intent_path(run_id)
        if not path.is_file():
            return None, None
        try:
            intent = self.core.load_yaml_document(path)
        except (OSError, ValueError, TypeError) as exc:
            return None, f"journal unreadable: {exc}"
        error = self._validate_completion_intent(intent, run, assignment, path)
        return (intent, None) if error is None else (None, error)

    def _validate_completion_intent(
        self,
        intent: Any,
        run: dict[str, Any],
        assignment: dict[str, Any],
        journal_path: Path,
    ) -> str | None:
        if not isinstance(intent, dict) or intent.get("kind") != "pf.process.completion-intent":
            return "journal kind is invalid"
        content = {key: value for key, value in intent.items() if key != "fingerprint"}
        try:
            if intent.get("fingerprint") != canonical_fingerprint(content):
                return "journal content fingerprint mismatch"
        except (TypeError, ValueError, RecursionError):
            return "journal content is invalid"
        run_id = str(run.get("id") or "")
        assignment_id = str(assignment.get("id") or "")
        if intent.get("run_id") != run_id or intent.get("assignment_id") != assignment_id:
            return "journal identity does not match selected work"
        final = intent.get("final") if isinstance(intent.get("final"), dict) else {}
        final_run = final.get("run") if isinstance(final.get("run"), dict) else {}
        final_assignment = final.get("assignment") if isinstance(final.get("assignment"), dict) else {}
        if final_run.get("id") != run_id or final_assignment.get("id") != assignment_id or final_assignment.get("run_id") != run_id:
            return "journal final payload identity is invalid"
        if final_run.get("status") != "completed" or final_assignment.get("status") not in TERMINAL_ASSIGNMENT_STATUSES:
            return "journal final payload is not terminal"
        if final_assignment.get("status") != "done":
            return "journal final assignment is not done"
        tasks = final_run.get("tasks") if isinstance(final_run.get("tasks"), list) else []
        task = next((item for item in tasks if isinstance(item, dict) and str(item.get("id") or "") == assignment_id), None)
        if not isinstance(task, dict) or task.get("status") not in {"done", "completed"}:
            return "journal final task status is invalid"
        if self._effective_process(final_run)[1] != "pinned":
            return "journal final process pin is invalid"
        pin = intent.get("process_execution") if isinstance(intent.get("process_execution"), dict) else {}
        current_pin = run.get("process_execution") if isinstance(run.get("process_execution"), dict) else {}
        for key in ["process_id", "process_version", "process_fingerprint", "snapshot_id", "snapshot_checksum"]:
            if str(pin.get(key) or "") != str(current_pin.get(key) or "") or str(pin.get(key) or "") != str((final_run.get("process_execution") or {}).get(key) or ""):
                return f"journal process pin mismatch: {key}"
        expected = {
            "journal_path": self.core.rel(journal_path, self.project_root),
            "run_path": self.core.rel(self._run_path(run_id), self.project_root),
            "assignment_path": self.core.rel(self._assignment_path(assignment_id), self.project_root),
        }
        if str(intent.get("journal_path") or "") != expected["journal_path"]:
            return "journal path is not owned by the selected run"
        owner = intent.get("owner") if isinstance(intent.get("owner"), dict) else {}
        if owner.get("run_path") != expected["run_path"] or owner.get("assignment_path") != expected["assignment_path"]:
            return "journal owner paths are invalid"
        if hasattr(self.core, "project_id") and str(owner.get("project_id") or "") != str(self.core.project_id(self.project_root)):
            return "journal project owner is invalid"
        final_paths = {
            "summary": self.core.rel(self._run_path(run_id).parent / "summary.md", self.project_root),
            "handoff": self.core.rel(self._flow_root() / "handoffs" / "runs" / f"{run_id}-handoff.md", self.project_root),
            "task_index": self.core.rel(self._run_path(run_id).parent / "task-index.md", self.project_root),
            "projection": self.core.rel(self._flow_root() / "artifacts" / "projections" / "process-execution-state.json", self.project_root),
        }
        for key, expected_path in final_paths.items():
            item = final.get(key) if isinstance(final.get(key), dict) else {}
            if str(item.get("path") or "") != expected_path:
                return f"journal {key} path is invalid"
        events = final.get("events")
        if not isinstance(events, list) or not events or any(not isinstance(item, dict) or not item.get("event_type") or not item.get("event_id") for item in events):
            return "journal event metadata is invalid"
        return None

    def _replay_completion_intent(self, intent: dict[str, Any], *, session_id: str = "", remove_intent: bool = True) -> dict[str, Any]:
        run_id = str(intent["run_id"])
        assignment_id = str(intent["assignment_id"])
        final = intent["final"]
        final_assignment = copy.deepcopy(final["assignment"])
        final_run = copy.deepcopy(final["run"])
        self._atomic_yaml(self._assignment_path(assignment_id), final_assignment)
        self._atomic_yaml(self._run_path(run_id), final_run)
        self._atomic_text(self._run_path(run_id).parent / "summary.md", str(final["summary"].get("content") or ""))
        self._atomic_text(self._flow_root() / "handoffs" / "runs" / f"{run_id}-handoff.md", str(final["handoff"].get("content") or ""))
        self._atomic_text(self._run_path(run_id).parent / "task-index.md", str(final["task_index"].get("content") or ""))
        result_state = self.state(run_id=run_id, assignment_id=assignment_id, session_id=session_id)
        self._write_projection(result_state)
        stage_id = str(final_assignment.get("stage") or "")
        for event in final["events"]:
            self._emit(
                str(event["event_type"]),
                final_run,
                final_assignment,
                str(event.get("stage_id") or stage_id),
                outcome=str(event.get("outcome") or "completed"),
                previous_stage_id=str(event.get("previous_stage_id") or stage_id),
                next_stage_id=str(event.get("next_stage_id") or ""),
                event_id=str(event["event_id"]),
            )
        if remove_intent:
            self._completion_intent_path(run_id).unlink(missing_ok=True)
        return {**result_state, "action": "run_completed", "previous_stage_id": stage_id, "next_stage_id": "", "recovered": True}

    def _complete_locked(self, run: dict[str, Any], assignment: dict[str, Any], process: dict[str, Any], *, outcome: str, notes: str, completed_at: str) -> None:
        run_id = str(run["id"])
        assignment_id = str(assignment["id"])
        assignment["stage_status"] = "completed"
        assignment["status"] = "done"
        assignment["updated_at"] = completed_at
        artifacts = [str(item.get("path")) for item in self._accumulated_evidence(assignment) if isinstance(item, dict) and item.get("path")]
        assignment["result"] = {"status": "done", "summary": str(notes or f"Completed declarative process with outcome {outcome}."), "artifacts": sorted(set(artifacts))}
        self._set_run_task_status(run, assignment_id, "done")
        run["status"] = "completed"
        run["updated_at"] = completed_at
        summary_path = self._run_path(run_id).parent / "summary.md"
        handoff_path = self._flow_root() / "handoffs" / "runs" / f"{run_id}-handoff.md"
        summary = self._render_summary(run, assignment)
        handoff = f"# Run Handoff: {run_id}\n\nStatus: `completed`\n\nSummary: `{self.core.rel(summary_path, self.project_root)}`\n"
        run["final_artifacts"] = [self.core.rel(summary_path, self.project_root), self.core.rel(handoff_path, self.project_root)]
        emitted = run.setdefault("events", {}).setdefault("emitted", []) if isinstance(run.setdefault("events", {}), dict) else []
        for event_type in ["process.stage.completed", "process.stage.transitioned", "task.completed", "assignment.completed", "run.completed", "run.summary.created"]:
            if isinstance(emitted, list) and event_type not in emitted:
                emitted.append(event_type)
        self._atomic_yaml(self._assignment_path(assignment_id), assignment)
        self._atomic_yaml(self._run_path(run_id), run)
        self._atomic_text(summary_path, summary)
        self._atomic_text(handoff_path, handoff)
        self._write_task_index(run)

    def _render_summary(self, run: dict[str, Any], assignment: dict[str, Any]) -> str:
        history = assignment.get("stage_history") if isinstance(assignment.get("stage_history"), list) else []
        lines = [f"# Run Summary: {run.get('title', run.get('id'))}", "", f"- run_id: `{run.get('id')}`", "- status: `completed`", f"- process: `{run.get('process')}`", "", "## Stage History", ""]
        lines.extend(f"- `{item.get('stage_id')}`: `{item.get('status')}` (`{item.get('outcome')}`)" for item in history if isinstance(item, dict))
        if not history:
            lines.append("- No stage history recorded.")
        return "\n".join(lines) + "\n"

    def _write_capsule(self, run: dict[str, Any], assignment: dict[str, Any], pin: dict[str, Any]) -> tuple[str, str]:
        path = self._flow_root() / "contexts" / "assignment-capsules" / f"{assignment['id']}.capsule.yaml"
        capsule = {
            "schema_version": 1,
            "capsule": {"id": f"{assignment['id']}-capsule", "generated_at": self.core.now_utc(), "assignment_id": assignment["id"], "assignment_path": f".pf/assignments/{assignment['id']}.yaml", "immutable": True, "worker_may_rebuild_context": False},
            "context_snapshot": {"id": pin["snapshot_id"], "sha256": pin["snapshot_checksum"], "freshness_at_creation": "fresh"},
            "context": {
                "snapshot_id": pin["snapshot_id"],
                "freshness": "fresh",
                "required_sources": [],
                "context_artifacts": [],
                "selected_specializations": _stable_ids(assignment.get("selected_specializations")),
                "applied_project_overrides": [],
                "selected_resource_ids": _stable_ids(pin.get("selected_resource_ids")),
            },
            "assignment": {"id": assignment["id"], "run_id": run["id"], "objective": assignment["objective"], "stage": assignment["stage"]},
            "process_execution": copy.deepcopy(pin),
        }
        self._atomic_yaml(path, capsule)
        return self.core.rel(path, self.project_root), "sha256:" + self._sha256_file(path)

    def _write_projection(self, state: dict[str, Any]) -> None:
        path = self._flow_root() / "artifacts" / "projections" / "process-execution-state.json"
        payload = {"schema_version": 1, "kind": "process-execution-state", "generated_at": self.core.now_utc(), "source": {"authority": "run+assignment+pinned-process"}, "state": state}
        self._atomic_text(path, json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n")

    def _write_task_index(self, run: dict[str, Any]) -> None:
        path = self._run_path(str(run["id"])).parent / "task-index.md"
        if hasattr(self.core, "render_task_index"):
            text = self.core.render_task_index(self.project_root, run)
        else:
            lines = [f"# Task Index: {run['id']}", ""]
            lines.extend(f"- `{item.get('id')}`: `{item.get('status')}`" for item in run.get("tasks", []) if isinstance(item, dict))
            text = "\n".join(lines) + "\n"
        self._atomic_text(path, text)

    def _emit(self, event_type: str, run: dict[str, Any], assignment: dict[str, Any], stage_id: str, *, outcome: str, previous_stage_id: str = "", next_stage_id: str = "", blockers: list[dict[str, Any]] | None = None, event_id: str | None = None) -> None:
        if not hasattr(self.core, "emit_process_event"):
            return
        self.core.emit_process_event(
            self.project_root,
            event_type,
            process_id=str(run.get("process") or ""),
            process_version=str((run.get("process_execution") or {}).get("process_version") or ""),
            stage=stage_id,
            subject=str(assignment.get("id") or run.get("id") or event_type),
            assignment_id_value=str(assignment.get("id") or ""),
            assignment_path=f".pf/assignments/{assignment.get('id')}.yaml" if assignment.get("id") else None,
            payload={
                "run_id": str(run.get("id") or ""),
                "assignment_id": str(assignment.get("id") or ""),
                "process_id": str(run.get("process") or ""),
                "stage_id": stage_id,
                "previous_stage_id": previous_stage_id,
                "next_stage_id": next_stage_id,
                "outcome": outcome,
                "blockers": blockers or [],
            },
            correlation_id=f"run-{run.get('id')}",
            event_id=event_id,
        )

    @contextlib.contextmanager
    def _start_lock(self) -> Iterator[None]:
        if hasattr(self.core, "registry_file_lock"):
            with self.core.registry_file_lock(self._flow_root() / "runs" / ".process-execution-start.yaml"):
                yield
        else:
            yield

    @contextlib.contextmanager
    def _run_lock(self, run_id: str) -> Iterator[None]:
        if hasattr(self.core, "registry_file_lock"):
            with self.core.registry_file_lock(self._run_path(run_id)):
                yield
        else:
            yield

    def _set_run_task_status(self, run: dict[str, Any], assignment_id: str, status: str) -> None:
        tasks = run.get("tasks") if isinstance(run.get("tasks"), list) else []
        for item in tasks:
            if isinstance(item, dict) and str(item.get("id") or "") == assignment_id:
                item["status"] = status

    def _atomic_yaml(self, path: Path, value: dict[str, Any]) -> None:
        self._atomic_text(path, self.core.dump_yaml(value).rstrip() + "\n")

    def _atomic_text(self, path: Path, content: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
        temporary.write_text(content, encoding="utf-8")
        temporary.replace(path)

    def _load_run(self, run_id: str) -> dict[str, Any]:
        return self.core.load_yaml_document(self._run_path(run_id))

    def _load_assignment(self, assignment_id: str) -> dict[str, Any]:
        return self.core.load_yaml_document(self._assignment_path(assignment_id))

    def _run_path(self, run_id: str) -> Path:
        return self._flow_root() / "runs" / self._validated_id(run_id, "run") / "run.yaml"

    def _assignment_path(self, assignment_id: str) -> Path:
        return self._flow_root() / "assignments" / f"{self._validated_id(assignment_id, 'assignment')}.yaml"

    def _validated_id(self, value: str, kind: str) -> str:
        identifier = str(value or "")
        if not SAFE_ID_RE.fullmatch(identifier):
            raise ValueError(f"unsafe {kind} id: {identifier!r}")
        return identifier

    def _flow_root(self) -> Path:
        return self.core.locate_flow_root(self.project_root)

    def _unique_id(self, root: Path, seed: str) -> str:
        base = "-".join(str(seed or "work").lower().split())[:72].strip("-") or "work"
        candidate = base
        index = 2
        while (root / candidate).exists() or (root / f"{candidate}.yaml").exists():
            suffix = f"-{index}"
            candidate = base[: 72 - len(suffix)] + suffix
            index += 1
        return candidate

    def _sha256_file(self, path: Path) -> str:
        return hashlib.sha256(path.read_bytes()).hexdigest()

    def _string_list(self, value: Any) -> list[str]:
        return [str(item) for item in value if str(item)] if isinstance(value, list) else []

    def _blocked(self, reason: str, *, action: str = "blocked", **extra: Any) -> dict[str, Any]:
        return {"schema_version": 1, "kind": "pf.work.execution", "action": action, "reason": reason, **extra}
