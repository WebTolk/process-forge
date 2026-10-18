"""Existing WorkSelectionService responsibilities with explicit operation dependencies."""
from __future__ import annotations

import copy
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable



@dataclass(frozen=True, kw_only=True)
class WorkSelectionService:
    bound_selection: Callable[[str], dict[str, Any] | None] = field(repr=False, compare=False)
    valid_selector: Callable[[str], bool] = field(repr=False, compare=False)
    records: Callable[..., list[dict[str, Any]]] = field(repr=False, compare=False)
    prefer: Callable[[list[dict[str, Any]], str], dict[str, Any] | None] = field(repr=False, compare=False)
    load_run: Callable[[str], dict[str, Any]] = field(repr=False, compare=False)
    load_assignment: Callable[[str], dict[str, Any]] = field(repr=False, compare=False)

    def select(self, *, run_id: str='', assignment_id: str='', session_id: str='') -> tuple[dict[str, Any], dict[str, Any]] | None:
        if not run_id and (not assignment_id) and session_id:
            
            binding = self.bound_selection(session_id)
            if binding:
                run_id, assignment_id = (binding['run_id'], binding['assignment_id'])
        for value in (run_id, assignment_id):
            if value and (not isinstance(value, str) or not self.valid_selector(value)):
                raise ValueError('invalid_work_selector')
        if run_id and assignment_id:
            run, assignment = self.load_run(run_id), self.load_assignment(assignment_id)
            if self._canonical_pair(run, assignment, run_id, assignment_id):
                # Exact canonical identity is authoritative only after proof.
                # Keep the final live reads; never return the preflight bodies.
                run, assignment = self.load_run(run_id), self.load_assignment(assignment_id)
                if not self._canonical_pair(run, assignment, run_id, assignment_id):
                    raise ValueError('work_identity_mismatch')
                return run, assignment
        records = self.records(include_historical=True)
        if assignment_id:
            record = next((item for item in records if item['assignment_id'] == assignment_id), None)
        elif run_id:
            candidates = [item for item in records if item['run_id'] == run_id]
            if len(candidates) > 1:
                raise ValueError('assignment_choice_required')
            record = self.prefer(candidates, session_id)
        else:
            active = [item for item in records if item['active']]
            record = self.prefer(active, session_id)
        if not record:
            return None
        if run_id and record['run_id'] != run_id:
            raise ValueError('work_identity_mismatch')
        return (self.load_run(record['run_id']), self.load_assignment(record['assignment_id']))

    def _canonical_pair(self, run: dict[str, Any], assignment: dict[str, Any], run_id: str, assignment_id: str) -> bool:
        if not (isinstance(run, dict) and isinstance(assignment, dict)
                and run.get('id') == run_id and assignment.get('id') == assignment_id
                and isinstance(run.get('tasks'), list)):
            return False
        try:
            from .context import _run_matches
        except ModuleNotFoundError as exc:
            # Optional PyYAML is needed by the shared context module. Without
            # that proof, keep the existing raw-reader/catalog fallback.
            if exc.name != 'yaml':
                raise
            return False
        return _run_matches(run, assignment)

    def preferred_record(self, records: list[dict[str, Any]], session_id: str) -> dict[str, Any] | None:
        if session_id:
            bound = [item for item in records if item.get('session_id') == session_id]
            if bound:
                records = bound
        return max(records, key=lambda item: (item.get('updated_at', ''), item.get('created_at', ''), item.get('assignment_id', ''))) if records else None

    def find_by_objective(self, objective: str) -> dict[str, Any]:
        normalized = ' '.join(objective.casefold().split())
        matches = [item for item in self.records(include_historical=True) if ' '.join(item['objective'].casefold().split()) == normalized]
        active = self.prefer([item for item in matches if item['active']], '')
        historical = [item for item in matches if not item['active']]
        return {'active': active, 'historical': historical}
