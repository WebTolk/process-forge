"""Internal, I/O-free rules for a declarative Work-state read decision."""

from __future__ import annotations

import copy
from dataclasses import dataclass
from typing import Any, Callable

from processforge_core.evidence.authoring import project_authoring_reviews
from processforge_core.evidence.guidance import EvidenceGuidancePolicy

__all__ = ()


@dataclass(frozen=True)
class WorkStateDecision:
    action: str
    blockers: list[dict[str, Any]]


class WorkStatePolicy:
    def completion_requirements(
        self,
        process: dict[str, Any],
        stage: dict[str, Any],
        assignment: dict[str, Any],
        evidence: list[dict[str, Any]],
        incomplete: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        requirements = list(incomplete)
        stage_id = str(assignment.get("stage") or "")
        stage_completion = stage.get("stage_completion")
        process_completion = process.get("stage_completion")
        completion = (
            stage_completion
            if isinstance(stage_completion, dict)
            else process_completion
            if isinstance(process_completion, dict)
            else {}
        )
        if completion.get("evidence_required") is True and not evidence:
            requirements.append(
                {"code": "stage_evidence_required", "stage_id": stage_id}
            )
        raw_execution = assignment.get("stage_execution")
        execution = raw_execution if isinstance(raw_execution, dict) else {}
        if (
            completion.get("handoff_note_required") is True
            and not str(execution.get("notes") or "").strip()
        ):
            requirements.append({"code": "handoff_note_required", "stage_id": stage_id})
        return requirements

    def decide(
        self,
        run: dict[str, Any],
        assignment: dict[str, Any],
        validation: dict[str, Any],
        incomplete: list[dict[str, Any]],
    ) -> WorkStateDecision:
        stage_id = str(assignment.get("stage") or "")
        raw_execution = assignment.get("stage_execution")
        execution = raw_execution if isinstance(raw_execution, dict) else {}
        raw_blockers = execution.get("blockers")
        stored = raw_blockers if isinstance(raw_blockers, list) else []
        blockers = [copy.deepcopy(item) for item in stored if isinstance(item, dict)]
        if validation.get("status") == "blocked":
            blockers.append(
                {"code": validation.get("reason") or "execution_contract_invalid"}
            )
        if str(assignment.get("stage_status") or "") == "blocked" and not blockers:
            blockers.append({"code": "stage_marked_blocked", "stage_id": stage_id})
        if str(assignment.get("status") or "") in {"cancelled", "failed"} or str(
            run.get("status") or ""
        ) in {"cancelled", "failed"}:
            action = "work_terminal"
        elif str(run.get("status") or "") == "completed":
            action = "run_completed"
        elif blockers:
            action = "work_blocked"
        elif incomplete:
            action = "work_incomplete"
        else:
            action = "work_ready"
        return WorkStateDecision(action, blockers)

    def project_state(
        self,
        *,
        action: str,
        permissions: dict[str, Any],
        project_id: str,
        run: dict[str, Any],
        assignment: dict[str, Any],
        process: dict[str, Any],
        pin_status: str,
        stage_id: str,
        stage: dict[str, Any],
        decision: WorkStateDecision,
        contract_validation: dict[str, Any],
        required_inputs: list[dict[str, Any]],
        required_evidence: list[dict[str, Any]],
        obligations: list[dict[str, Any]],
        artifacts: list[dict[str, Any]],
        entry_gates: list[dict[str, Any]],
        exit_gates: list[dict[str, Any]],
        outcomes: list[dict[str, Any]],
        incomplete: list[dict[str, Any]],
        current_evidence: list[dict[str, Any]],
        fingerprint: Callable[[dict[str, Any]], str],
        stable_ids: Callable[[Any], list[str]],
    ) -> dict[str, Any]:
        state: dict[str, Any] = {
            "schema_version": 1,
            "kind": "pf.work.state",
            "action": action,
            "execution_readiness": permissions,
            "project": {"id": project_id},
            "process": {
                "id": str(process.get("id") or run.get("process") or ""),
                "version": str(process.get("version") or ""),
                "fingerprint": str(
                    (run.get("process_execution") or {}).get("process_fingerprint")
                    or fingerprint(process)
                ),
                "pin_status": pin_status,
            },
            "work": {
                "active_specializations": stable_ids(
                    assignment.get("selected_specializations")
                    or run.get("selected_specializations")
                ),
                "selected_resource_ids": stable_ids(
                    (run.get("process_execution") or {}).get("selected_resource_ids")
                ),
            },
            "context": {
                "id": f"{assignment['id']}-capsule",
                "checksum": (assignment.get("process_execution") or {}).get(
                    "assignment_capsule_checksum"
                ),
                "identity_source": "assignment_process_pin",
                "validation": contract_validation,
            },
            "run": {
                "id": str(run.get("id") or ""),
                "status": str(run.get("status") or ""),
            },
            "assignment": {
                "id": str(assignment.get("id") or ""),
                "status": str(assignment.get("status") or ""),
            },
            "stage": {
                "id": stage_id,
                "title": str(stage.get("title") or stage_id),
                "status": str(assignment.get("stage_status") or "in_progress"),
            },
            "required_inputs": required_inputs,
            "required_evidence": required_evidence,
            "obligations": obligations,
            "artifacts": artifacts,
            "gates": {"entry": entry_gates, "exit": exit_gates},
            "allowed_outcomes": outcomes,
            "blockers": decision.blockers,
            "incomplete": incomplete,
            "completion": {
                "status": "complete" if not incomplete else "incomplete",
                "requirements": incomplete,
            },
            "evidence": current_evidence,
        }
        state["evidence_guidance"] = EvidenceGuidancePolicy().project(
            state, process=process
        )
        state["authoring_review"] = project_authoring_reviews(
            assignment, current_evidence
        )
        return state
