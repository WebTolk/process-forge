"""Internal, I/O-free rules for a declarative Work-state read decision."""

from __future__ import annotations

import copy
from dataclasses import dataclass
from typing import Any

__all__ = ()


@dataclass(frozen=True)
class WorkStateDecision:
    action: str
    blockers: list[dict[str, Any]]


class WorkStatePolicy:
    def completion_requirements(
        self, process: dict[str, Any], stage: dict[str, Any], assignment: dict[str, Any],
        evidence: list[dict[str, Any]], incomplete: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        requirements = list(incomplete)
        stage_id = str(assignment.get("stage") or "")
        completion = stage.get("stage_completion") if isinstance(stage.get("stage_completion"), dict) else process.get("stage_completion") if isinstance(process.get("stage_completion"), dict) else {}
        if completion.get("evidence_required") is True and not evidence:
            requirements.append({"code": "stage_evidence_required", "stage_id": stage_id})
        execution = assignment.get("stage_execution") if isinstance(assignment.get("stage_execution"), dict) else {}
        if completion.get("handoff_note_required") is True and not str(execution.get("notes") or "").strip():
            requirements.append({"code": "handoff_note_required", "stage_id": stage_id})
        return requirements

    def decide(
        self, run: dict[str, Any], assignment: dict[str, Any],
        validation: dict[str, Any], incomplete: list[dict[str, Any]],
    ) -> WorkStateDecision:
        stage_id = str(assignment.get("stage") or "")
        execution = assignment.get("stage_execution") if isinstance(assignment.get("stage_execution"), dict) else {}
        stored = execution.get("blockers") if isinstance(execution.get("blockers"), list) else []
        blockers = [copy.deepcopy(item) for item in stored if isinstance(item, dict)]
        if validation.get("status") == "blocked":
            blockers.append({"code": validation.get("reason") or "execution_contract_invalid"})
        if str(assignment.get("stage_status") or "") == "blocked" and not blockers:
            blockers.append({"code": "stage_marked_blocked", "stage_id": stage_id})
        if str(assignment.get("status") or "") in {"cancelled", "failed"} or str(run.get("status") or "") in {"cancelled", "failed"}:
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
