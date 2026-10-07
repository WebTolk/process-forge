"""Existing CompletionDocumentService responsibilities with explicit operation dependencies."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable


@dataclass(frozen=True, kw_only=True)
class CompletionDocumentService:
    project_root: Path = field(repr=False, compare=False)
    run_path: Callable[[str], Path] = field(repr=False, compare=False)
    has_task_index: Callable[[], bool] = field(repr=False, compare=False)
    task_index: Callable[[Path, dict[str, Any]], str] = field(repr=False, compare=False)
    atomic_text: Callable[[Path, str], Any] = field(repr=False, compare=False)

    def summary(self, run: dict[str, Any], assignment: dict[str, Any]) -> str:
        history = assignment.get('stage_history') if isinstance(assignment.get('stage_history'), list) else []
        lines = [f"# Run Summary: {run.get('title', run.get('id'))}", '', f"- run_id: `{run.get('id')}`", '- status: `completed`', f"- process: `{run.get('process')}`", '', '## Stage History', '']
        lines.extend((f"- `{item.get('stage_id')}`: `{item.get('status')}` (`{item.get('outcome')}`)" for item in history if isinstance(item, dict)))
        if not history:
            lines.append('- No stage history recorded.')
        return '\n'.join(lines) + '\n'

    def write_task_index(self, run: dict[str, Any]) -> None:
        path = self.run_path(str(run['id'])).parent / 'task-index.md'
        if self.has_task_index():
            text = self.task_index(self.project_root, run)
        else:
            lines = [f"# Task Index: {run['id']}", '']
            lines.extend((f"- `{item.get('id')}`: `{item.get('status')}`" for item in run.get('tasks', []) if isinstance(item, dict)))
            text = '\n'.join(lines) + '\n'
        self.atomic_text(path, text)
