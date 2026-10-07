"""Existing CompletionIntentBuilder responsibilities with explicit operation dependencies."""
from __future__ import annotations

import copy
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable


import hashlib

@dataclass(frozen=True, kw_only=True)
class CompletionIntentBuilder:
    project_root: Path = field(repr=False, compare=False)
    accumulated_evidence: Callable[[dict[str, Any]], list[dict[str, Any]]] = field(repr=False, compare=False)
    set_task_status: Callable[[dict[str, Any], str, str], Any] = field(repr=False, compare=False)
    run_path: Callable[[str], Path] = field(repr=False, compare=False)
    assignment_path: Callable[[str], Path] = field(repr=False, compare=False)
    flow_root: Callable[[], Path] = field(repr=False, compare=False)
    summary: Callable[[dict[str, Any], dict[str, Any]], str] = field(repr=False, compare=False)
    has_task_index: Callable[[], bool] = field(repr=False, compare=False)
    task_index: Callable[[Path, dict[str, Any]], str] = field(repr=False, compare=False)
    rel: Callable[[Path, Path], str] = field(repr=False, compare=False)
    intent_path: Callable[[str], Path] = field(repr=False, compare=False)
    project_id: Callable[[Path], Any] = field(repr=False, compare=False)
    fingerprint: Callable[[Any], str] = field(repr=False, compare=False)

    def build(self, run: dict[str, Any], assignment: dict[str, Any], process: dict[str, Any], *, outcome: str, notes: str, completed_at: str) -> dict[str, Any]:
        """Build every terminal payload before the first terminal write.

            The journal is deliberately self-contained.  A retry therefore does
            not re-run evidence selection, call ``now_utc`` again, or infer a new
            outcome from partially written records.
            """
        run_id = str(run['id'])
        assignment_id = str(assignment['id'])
        final_assignment = copy.deepcopy(assignment)
        final_assignment['stage_status'] = 'completed'
        final_assignment['status'] = 'done'
        final_assignment['updated_at'] = completed_at
        artifacts = [str(item.get('path')) for item in self.accumulated_evidence(final_assignment) if isinstance(item, dict) and item.get('path')]
        final_assignment['result'] = {'status': 'done', 'summary': str(notes or f'Completed declarative process with outcome {outcome}.'), 'artifacts': sorted(set(artifacts))}
        final_run = copy.deepcopy(run)
        self.set_task_status(final_run, assignment_id, 'done')
        final_run['status'] = 'completed'
        final_run['updated_at'] = completed_at
        summary_path = self.run_path(run_id).parent / 'summary.md'
        handoff_path = self.flow_root() / 'handoffs' / 'runs' / f'{run_id}-handoff.md'
        task_index_path = self.run_path(run_id).parent / 'task-index.md'
        projection_path = self.flow_root() / 'artifacts' / 'projections' / 'process-execution-state.json'
        summary = self.summary(final_run, final_assignment)
        handoff = f'# Run Handoff: {run_id}\n\nStatus: `completed`\n\nSummary: `{self.rel(summary_path, self.project_root)}`\n'
        final_run['final_artifacts'] = [self.rel(summary_path, self.project_root), self.rel(handoff_path, self.project_root)]
        emitted = final_run.setdefault('events', {}).setdefault('emitted', []) if isinstance(final_run.setdefault('events', {}), dict) else []
        for event_type in ['process.stage.completed', 'process.stage.transitioned', 'task.completed', 'assignment.completed', 'run.completed', 'run.summary.created']:
            if isinstance(emitted, list) and event_type not in emitted:
                emitted.append(event_type)
        if self.has_task_index():
            task_index = self.task_index(self.project_root, final_run)
        else:
            lines = [f'# Task Index: {run_id}', '']
            lines.extend((f"- `{item.get('id')}`: `{item.get('status')}`" for item in final_run.get('tasks', []) if isinstance(item, dict)))
            task_index = '\n'.join(lines) + '\n'
        stage_id = str(assignment.get('stage') or '')
        intent_seed = f'{run_id}:{assignment_id}:{completed_at}:{outcome}'
        intent_id = 'completion-' + hashlib.sha256(intent_seed.encode('utf-8')).hexdigest()[:32]
        event_specs = []
        for event_type, event_stage in [('process.stage.completed', stage_id), ('process.stage.transitioned', stage_id), ('task.completed', stage_id), ('assignment.completed', stage_id), ('run.completed', stage_id), ('run.summary.created', stage_id)]:
            event_specs.append({'event_type': event_type, 'event_id': 'evt_' + hashlib.sha256(f'{intent_id}:{event_type}'.encode('utf-8')).hexdigest()[:32], 'stage_id': event_stage, 'previous_stage_id': stage_id, 'next_stage_id': '', 'outcome': outcome})
        pin = final_run.get('process_execution') if isinstance(final_run.get('process_execution'), dict) else {}
        expected_run_path = self.rel(self.run_path(run_id), self.project_root)
        expected_assignment_path = self.rel(self.assignment_path(assignment_id), self.project_root)
        expected_journal_path = self.rel(self.intent_path(run_id), self.project_root)
        intent = {'schema_version': 1, 'kind': 'pf.process.completion-intent', 'intent_id': intent_id, 'created_at': completed_at, 'completed_at': completed_at, 'run_id': run_id, 'assignment_id': assignment_id, 'journal_path': expected_journal_path, 'owner': {'project_id': self.project_id(self.project_root), 'run_path': expected_run_path, 'assignment_path': expected_assignment_path}, 'process_execution': copy.deepcopy(pin), 'final': {'run': final_run, 'assignment': final_assignment, 'summary': {'path': self.rel(summary_path, self.project_root), 'content': summary}, 'handoff': {'path': self.rel(handoff_path, self.project_root), 'content': handoff}, 'task_index': {'path': self.rel(task_index_path, self.project_root), 'content': task_index}, 'projection': {'path': self.rel(projection_path, self.project_root)}, 'events': event_specs}}
        intent['fingerprint'] = self.fingerprint(intent)
        return intent
