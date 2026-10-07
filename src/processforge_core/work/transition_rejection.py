"""Existing TransitionRejectionPolicy responsibilities with explicit operation dependencies."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

@dataclass(frozen=True, kw_only=True)
class TransitionRejectionPolicy:
    state: Callable[..., dict[str, Any]] = field(repr=False, compare=False)

    @staticmethod
    def is_recoverable(blocker: Any) -> bool:
        if not isinstance(blocker, dict):
            return False
        return str(blocker.get('code') or '') in {'invalid_evidence', 'not_applicable_evidence_incomplete', 'artifact_path_missing', 'outcome_not_allowed', 'invalid_process_definition'}

    def rejected(self, *, run: dict[str, Any], assignment: dict[str, Any], session_id: str, reason: str, blockers: list[dict[str, Any]]) -> dict[str, Any]:
        state = self.state(run_id=str(run.get('id') or ''), assignment_id=str(assignment.get('id') or ''), session_id=session_id)
        return {**state, 'action': 'transition_rejected', 'reason': reason, 'blockers': blockers}
