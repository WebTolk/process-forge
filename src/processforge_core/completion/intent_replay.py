"""Existing CompletionIntentReplayService responsibilities with explicit operation dependencies."""
from __future__ import annotations

import copy
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable


@dataclass(frozen=True, kw_only=True)
class CompletionIntentReplayService:
    assignment_path: Callable[[str], Path] = field(repr=False, compare=False)
    run_path: Callable[[str], Path] = field(repr=False, compare=False)
    flow_root: Callable[[], Path] = field(repr=False, compare=False)
    atomic_yaml: Callable[[Path, dict[str, Any]], Any] = field(repr=False, compare=False)
    atomic_text: Callable[[Path, str], Any] = field(repr=False, compare=False)
    state: Callable[..., dict[str, Any]] = field(repr=False, compare=False)
    write_projection: Callable[[dict[str, Any]], Any] = field(repr=False, compare=False)
    emit: Callable[..., Any] = field(repr=False, compare=False)
    intent_path: Callable[[str], Path] = field(repr=False, compare=False)

    def replay(self, intent: dict[str, Any], *, session_id: str='', remove_intent: bool=True) -> dict[str, Any]:
        run_id = str(intent['run_id'])
        assignment_id = str(intent['assignment_id'])
        final = intent['final']
        final_assignment = copy.deepcopy(final['assignment'])
        final_run = copy.deepcopy(final['run'])
        self.atomic_yaml(self.assignment_path(assignment_id), final_assignment)
        self.atomic_yaml(self.run_path(run_id), final_run)
        self.atomic_text(self.run_path(run_id).parent / 'summary.md', str(final['summary'].get('content') or ''))
        self.atomic_text(self.flow_root() / 'handoffs' / 'runs' / f'{run_id}-handoff.md', str(final['handoff'].get('content') or ''))
        self.atomic_text(self.run_path(run_id).parent / 'task-index.md', str(final['task_index'].get('content') or ''))
        result_state = self.state(run_id=run_id, assignment_id=assignment_id, session_id=session_id)
        self.write_projection(result_state)
        stage_id = str(final_assignment.get('stage') or '')
        for event in final['events']:
            self.emit(str(event['event_type']), final_run, final_assignment, str(event.get('stage_id') or stage_id), outcome=str(event.get('outcome') or 'completed'), previous_stage_id=str(event.get('previous_stage_id') or stage_id), next_stage_id=str(event.get('next_stage_id') or ''), event_id=str(event['event_id']))
        if remove_intent:
            self.intent_path(run_id).unlink(missing_ok=True)
        return {**result_state, 'action': 'run_completed', 'previous_stage_id': stage_id, 'next_stage_id': '', 'recovered': True}
