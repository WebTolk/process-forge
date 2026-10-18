"""Existing CompletionIntentValidationService responsibilities with explicit operation dependencies."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

@dataclass(frozen=True, kw_only=True)
class CompletionIntentValidationService:
    project_root: Path = field(repr=False, compare=False)
    fingerprint: Callable[[Any], str] = field(repr=False, compare=False)
    terminal_assignment_statuses: Callable[[], set[str]] = field(repr=False, compare=False)
    effective_process: Callable[[dict[str, Any]], tuple[dict[str, Any], str]] = field(repr=False, compare=False)
    rel: Callable[[Path, Path], str] = field(repr=False, compare=False)
    run_path: Callable[[str], Path] = field(repr=False, compare=False)
    assignment_path: Callable[[str], Path] = field(repr=False, compare=False)
    flow_root: Callable[[], Path] = field(repr=False, compare=False)
    has_project_id: Callable[[], bool] = field(repr=False, compare=False)
    project_id: Callable[[Path], Any] = field(repr=False, compare=False)

    def validate(self, intent: Any, run: dict[str, Any], assignment: dict[str, Any], journal_path: Path) -> str | None:
        if not isinstance(intent, dict) or intent.get('kind') != 'pf.process.completion-intent':
            return 'journal kind is invalid'
        content = {key: value for key, value in intent.items() if key != 'fingerprint'}
        try:
            if intent.get('fingerprint') != self.fingerprint(content):
                return 'journal content fingerprint mismatch'
        except (TypeError, ValueError, RecursionError):
            return 'journal content is invalid'
        run_id = str(run.get('id') or '')
        assignment_id = str(assignment.get('id') or '')
        if intent.get('run_id') != run_id or intent.get('assignment_id') != assignment_id:
            return 'journal identity does not match selected work'
        final = intent.get('final') if isinstance(intent.get('final'), dict) else {}
        final_run = final.get('run') if isinstance(final.get('run'), dict) else {}
        final_assignment = final.get('assignment') if isinstance(final.get('assignment'), dict) else {}
        if final_run.get('id') != run_id or final_assignment.get('id') != assignment_id or final_assignment.get('run_id') != run_id:
            return 'journal final payload identity is invalid'
        if final_run.get('status') != 'completed' or final_assignment.get('status') not in self.terminal_assignment_statuses():
            return 'journal final payload is not terminal'
        if final_assignment.get('status') != 'done':
            return 'journal final assignment is not done'
        tasks = final_run.get('tasks') if isinstance(final_run.get('tasks'), list) else []
        task = next((item for item in tasks if isinstance(item, dict) and str(item.get('id') or '') == assignment_id), None)
        if not isinstance(task, dict) or task.get('status') not in {'done', 'completed'}:
            return 'journal final task status is invalid'
        if self.effective_process(final_run)[1] != 'pinned':
            return 'journal final process pin is invalid'
        pin = intent.get('process_execution') if isinstance(intent.get('process_execution'), dict) else {}
        current_pin = run.get('process_execution') if isinstance(run.get('process_execution'), dict) else {}
        for key in ['process_id', 'process_version', 'process_fingerprint', 'snapshot_id', 'snapshot_checksum']:
            if str(pin.get(key) or '') != str(current_pin.get(key) or '') or str(pin.get(key) or '') != str((final_run.get('process_execution') or {}).get(key) or ''):
                return f'journal process pin mismatch: {key}'
        expected = {'journal_path': self.rel(journal_path, self.project_root), 'run_path': self.rel(self.run_path(run_id), self.project_root), 'assignment_path': self.rel(self.assignment_path(assignment_id), self.project_root)}
        if str(intent.get('journal_path') or '') != expected['journal_path']:
            return 'journal path is not owned by the selected run'
        owner = intent.get('owner') if isinstance(intent.get('owner'), dict) else {}
        if owner.get('run_path') != expected['run_path'] or owner.get('assignment_path') != expected['assignment_path']:
            return 'journal owner paths are invalid'
        if self.has_project_id() and str(owner.get('project_id') or '') != str(self.project_id(self.project_root)):
            return 'journal project owner is invalid'
        final_paths = {'summary': self.rel(self.run_path(run_id).parent / 'summary.md', self.project_root), 'handoff': self.rel(self.flow_root() / 'handoffs' / 'runs' / f'{run_id}-handoff.md', self.project_root), 'task_index': self.rel(self.run_path(run_id).parent / 'task-index.md', self.project_root), 'projection': self.rel(self.flow_root() / 'artifacts' / 'projections' / 'process-execution-state.json', self.project_root)}
        for key, expected_path in final_paths.items():
            item = final.get(key) if isinstance(final.get(key), dict) else {}
            if str(item.get('path') or '') != expected_path:
                return f'journal {key} path is invalid'
        events = final.get('events')
        if not isinstance(events, list) or not events or any((not isinstance(item, dict) or not item.get('event_type') or (not item.get('event_id')) for item in events)):
            return 'journal event metadata is invalid'
        return None
