"""Existing RunCompletionPolicy responsibilities with explicit operation dependencies."""
from __future__ import annotations

import copy
from dataclasses import dataclass, field
from typing import Any, Callable

@dataclass(frozen=True, kw_only=True)
class RunCompletionPolicy:
    accumulated_evidence: Callable[[dict[str, Any]], list[dict[str, Any]]] = field(repr=False, compare=False)
    string_list: Callable[[Any], list[str]] = field(repr=False, compare=False)
    gate_state: Callable[..., dict[str, Any]] = field(repr=False, compare=False)

    def blockers(self, process: dict[str, Any], run: dict[str, Any], assignment: dict[str, Any]) -> list[dict[str, Any]]:
        completion = process.get('run_completion') if isinstance(process.get('run_completion'), dict) else {}
        evidence = self.accumulated_evidence(assignment)
        blockers: list[dict[str, Any]] = []
        for gate_id in self.string_list(completion.get('gates')):
            gate = self.gate_state(process, gate_id, evidence, phase='run_completion')
            if gate['required'] and gate['blocking'] and (not gate['satisfied']):
                blocker = {'code': 'run_completion_gate_missing', 'gate_id': gate_id}
                if isinstance(gate.get('diagnostic'), dict):
                    blocker['diagnostic'] = copy.deepcopy(gate['diagnostic'])
                blockers.append(blocker)
        assignment_id = str(assignment.get('id') or '')
        for task in run.get('tasks', []) if isinstance(run.get('tasks'), list) else []:
            if not isinstance(task, dict) or str(task.get('id') or '') == assignment_id or task.get('blocking', True) is False:
                continue
            if str(task.get('status') or '') not in {'done', 'completed', 'cancelled'}:
                blockers.append({'code': 'blocking_assignment_incomplete', 'assignment_id': str(task.get('id') or ''), 'status': str(task.get('status') or '')})
        return blockers

    def set_task_status(self, run: dict[str, Any], assignment_id: str, status: str) -> None:
        tasks = run.get('tasks') if isinstance(run.get('tasks'), list) else []
        for item in tasks:
            if isinstance(item, dict) and str(item.get('id') or '') == assignment_id:
                item['status'] = status
