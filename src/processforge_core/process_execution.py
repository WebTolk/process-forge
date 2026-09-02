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

    def start(self, *, objective: str, session_id: str = "", stage_override: str = "") -> dict[str, Any]:
        with self._start_lock():
            return self._start_locked(objective=objective, session_id=session_id, stage_override=stage_override)

    def _start_locked(self, *, objective: str, session_id: str = "", stage_override: str = "") -> dict[str, Any]:
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

        process_id = self._selected_process_id()
        definition = self.core.resolve_process_definition(self.project_root, process_id)
        process = copy.deepcopy(definition.process)
        stages = executable_stages(process)
        if not stages:
            return self._blocked("process_has_no_executable_stages", process_id=process_id)
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
            return self._blocked("invalid_process_definition", message=str(exc), process_id=process_id)

        now = self.core.now_utc()
        flow_root = self._flow_root()
        run_id = self._unique_id(flow_root / "runs", "garage-" + self.core.safe_id(objective, "work"))
        assignment_id = self._unique_id(flow_root / "assignments", self.core.safe_id(objective, "task"))
        pin = self._process_pin(process, definition.path)
        run = {
            "schema_version": 1,
            "id": run_id,
            "title": objective[:80],
            "process": process_id,
            "status": "in_progress",
            "created_at": now,
            "updated_at": now,
            "objective": objective,
            "platform": "",
            "selected_specializations": [],
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
            "process": process_id,
            "status": "in_progress",
            "created_at": now,
            "updated_at": now,
            "objective": objective,
            "platform": "",
            "selected_specializations": [],
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
            if str(run.get("status") or "") in TERMINAL_RUN_STATUSES or str(assignment.get("status") or "") in TERMINAL_ASSIGNMENT_STATUSES:
                return self._blocked("work_is_terminal", run_id=run.get("id"), assignment_id=assignment.get("id"), run_status=run.get("status"), assignment_status=assignment.get("status"))
            process, pin_status = self._effective_process(run)
            if pin_status != "pinned":
                return self._blocked("process_pin_invalid", run_id=run.get("id"), assignment_id=assignment.get("id"), pin_status=pin_status)
            stage_id = str(assignment.get("stage") or "")
            normalized_evidence, evidence_blockers = self._normalize_evidence(evidence)
            stage_execution = assignment.get("stage_execution") if isinstance(assignment.get("stage_execution"), dict) else {}
            stage_execution = {**stage_execution, "evidence": self._merge_evidence(stage_execution.get("evidence"), normalized_evidence), "notes": str(notes or stage_execution.get("notes") or "")}
            assignment["stage_execution"] = stage_execution
            assignment["updated_at"] = self.core.now_utc()
            self._atomic_yaml(self._assignment_path(str(assignment["id"])), assignment)
            preview = self.state(run_id=str(run.get("id") or ""), assignment_id=str(assignment.get("id") or ""), session_id=session_id)
            preview_blockers = list(preview.get("blockers") or [])
            preview_incomplete = list(preview.get("incomplete") or [])
            outcomes = {str(item.get("id")): item for item in preview.get("allowed_outcomes", []) if isinstance(item, dict)}
            if outcome not in outcomes:
                preview_blockers.append({"code": "outcome_not_allowed", "outcome": outcome, "allowed": sorted(outcomes)})
            preview_blockers.extend(evidence_blockers)
            next_stage_id = str(outcomes.get(outcome, {}).get("next_stage") or "")
            if next_stage_id:
                next_stage = self._stage(process, next_stage_id)
                accumulated = self._accumulated_evidence(assignment)
                for gate_id in self._string_list(next_stage.get("entry_gates")):
                    gate = self._gate_state(process, gate_id, accumulated, phase="entry")
                    if not gate["satisfied"] and gate.get("blocking", True):
                        preview_incomplete.append({"code": "entry_gate_evidence_missing", "gate_id": gate_id, "stage_id": next_stage_id})
            if preview_blockers:
                now = self.core.now_utc()
                assignment["stage_status"] = "blocked"
                assignment["updated_at"] = now
                assignment["stage_execution"]["blocked_at"] = now
                assignment["stage_execution"]["blockers"] = preview_blockers
                self._atomic_yaml(self._assignment_path(str(assignment["id"])), assignment)
                blocked_state = self.state(run_id=str(run["id"]), assignment_id=str(assignment["id"]), session_id=session_id)
                self._write_projection(blocked_state)
                self._emit("process.stage.blocked", run, assignment, stage_id, outcome=outcome, previous_stage_id=stage_id, next_stage_id=next_stage_id, blockers=preview_blockers)
                return {**blocked_state, "action": "blocked", "reason": "stage_transition_blocked", "blockers": preview_blockers}

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
                self._complete_locked(run, assignment, process, outcome=outcome, notes=notes, completed_at=now)
                action = "run_completed"

            result_state = self.state(run_id=str(run["id"]), assignment_id=str(assignment["id"]), session_id=session_id)
            self._write_projection(result_state)
            self._emit("process.stage.completed", run, assignment, previous_stage_id, outcome=outcome, previous_stage_id=previous_stage_id, next_stage_id=next_stage_id)
            self._emit("process.stage.transitioned", run, assignment, next_stage_id or previous_stage_id, outcome=outcome, previous_stage_id=previous_stage_id, next_stage_id=next_stage_id)
            if next_stage_id:
                self._emit("process.stage.started", run, assignment, next_stage_id, outcome="started", previous_stage_id=previous_stage_id, next_stage_id=next_stage_id)
            else:
                self._emit("task.completed", run, assignment, previous_stage_id, outcome=outcome)
                self._emit("assignment.completed", run, assignment, previous_stage_id, outcome=outcome)
                self._emit("run.completed", run, assignment, previous_stage_id, outcome=outcome)
                self._emit("run.summary.created", run, assignment, previous_stage_id, outcome=outcome)
            return {**result_state, "action": action, "previous_stage_id": previous_stage_id, "next_stage_id": next_stage_id}

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
        readiness = self.can_complete(run_id=run_id, assignment_id=assignment_id, session_id=session_id)
        if readiness["blockers"] and not evidence:
            return {"schema_version": 1, "kind": "pf.work.complete", "action": "blocked", **readiness}
        return self.transition(outcome=outcome, evidence=evidence, notes=notes, run_id=run_id, assignment_id=assignment_id, session_id=session_id)

    def _context_check(self) -> dict[str, Any]:
        explicit = ""
        if self.workplace_root and (self.workplace_root / "workplace.yaml").is_file():
            explicit = str(self.workplace_root)
        return self.core.project_context_check_result(self.project_root, explicit_workplace=explicit or None)

    def _selected_process_id(self) -> str:
        manifest = self.core.load_yaml_document(self._flow_root() / "process-forge.yaml")
        return str(manifest.get("process") or "task-batch-execution").strip()

    def _process_pin(self, process: dict[str, Any], source_path: Path) -> dict[str, Any]:
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
        }

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
                active = status in ACTIVE_ASSIGNMENT_STATUSES and str(run.get("status") or "") in ACTIVE_RUN_STATUSES
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
                and str(item.get("status") or "") in statuses
            ),
            None,
        )
        return {"id": identifier, "kind": kind, "satisfied": match is not None, "evidence": match or {}}

    def _gate_state(self, process: dict[str, Any], gate_id: str, evidence: list[dict[str, Any]], *, phase: str) -> dict[str, Any]:
        definitions = process.get("gates") if isinstance(process.get("gates"), list) else []
        definition = next((item for item in definitions if isinstance(item, dict) and str(item.get("id") or "") == gate_id), {})
        match = next(
            (
                item
                for item in reversed(evidence)
                if str(item.get("kind") or "") == "gate"
                and str(item.get("gate_id") or item.get("id") or "") == gate_id
                and str(item.get("status") or "") in {"passed", "approved", "not_applicable"}
            ),
            None,
        )
        return {
            "id": gate_id,
            "phase": phase,
            "type": str(definition.get("type") or "checklist"),
            "blocking": bool(definition.get("blocking", True)),
            "required": bool(definition.get("required", True)),
            "satisfied": match is not None,
            "evidence": match or {},
        }

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
        requirements.extend({"code": "required_input_missing", "input_id": item["id"]} for item in inputs if not item["satisfied"])
        requirements.extend({"code": "artifact_evidence_missing", "artifact_id": item["id"]} for item in artifacts if not item["satisfied"])
        requirements.extend({"code": "required_evidence_missing", "evidence_id": item["id"]} for item in required_evidence if not item["satisfied"])
        requirements.extend({"code": "gate_evidence_missing", "gate_id": item["id"]} for item in gates if item["required"] and item["blocking"] and not item["satisfied"])
        requirements.extend({"code": "automation_not_ready", "obligation_id": item["id"], "status": item["status"]} for item in obligations if item["status"] != "ready")
        return requirements

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
                if safe_path is None or not safe_path.is_file():
                    blockers.append({"code": "artifact_path_missing", "index": index, "path": path_value})
                    continue
                else:
                    item["path"] = self.core.rel(safe_path, self.project_root)
                    item["sha256"] = "sha256:" + self._sha256_file(safe_path)
            normalized.append(item)
        return normalized, blockers

    def _safe_evidence_path(self, value: str) -> Path | None:
        path = Path(value)
        if path.is_absolute():
            return None
        resolved = (self.project_root / path).resolve()
        try:
            resolved.relative_to(self.project_root.resolve())
        except ValueError:
            return None
        return resolved

    def _merge_evidence(self, existing: Any, incoming: list[dict[str, Any]]) -> list[dict[str, Any]]:
        values = [copy.deepcopy(item) for item in existing if isinstance(item, dict)] if isinstance(existing, list) else []
        for item in incoming:
            marker = (str(item.get("kind") or ""), str(item.get("gate_id") or item.get("artifact_id") or item.get("input_id") or item.get("id") or ""))
            values = [current for current in values if (str(current.get("kind") or ""), str(current.get("gate_id") or current.get("artifact_id") or current.get("input_id") or current.get("id") or "")) != marker]
            values.append(item)
        return values

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
                blockers.append({"code": "run_completion_gate_missing", "gate_id": gate_id})
        assignment_id = str(assignment.get("id") or "")
        for task in run.get("tasks", []) if isinstance(run.get("tasks"), list) else []:
            if not isinstance(task, dict) or str(task.get("id") or "") == assignment_id or task.get("blocking", True) is False:
                continue
            if str(task.get("status") or "") not in {"done", "completed", "cancelled"}:
                blockers.append({"code": "blocking_assignment_incomplete", "assignment_id": str(task.get("id") or ""), "status": str(task.get("status") or "")})
        return blockers

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
                "selected_specializations": [],
                "applied_project_overrides": [],
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

    def _emit(self, event_type: str, run: dict[str, Any], assignment: dict[str, Any], stage_id: str, *, outcome: str, previous_stage_id: str = "", next_stage_id: str = "", blockers: list[dict[str, Any]] | None = None) -> None:
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
