"""Existing CompletionIntentReadService responsibilities with explicit operation dependencies."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable


@dataclass(frozen=True, kw_only=True)
class CompletionIntentReadService:
    run_path: Callable[[str], Path] = field(repr=False, compare=False)
    intent_path: Callable[[str], Path] = field(repr=False, compare=False)
    valid_id: Callable[[str], bool] = field(repr=False, compare=False)
    load_document: Callable[[Path], dict[str, Any]] = field(repr=False, compare=False)
    validate: Callable[[Any, dict[str, Any], dict[str, Any], Path], str | None] = field(repr=False, compare=False)

    def path(self, run_id: str) -> Path:
        return self.run_path(run_id).parent / 'completion-intent.yaml'

    def load(self, run: dict[str, Any], assignment: dict[str, Any]) -> tuple[dict[str, Any] | None, str | None]:
        run_id = str(run.get('id') or '')
        assignment_id = str(assignment.get('id') or '')
        if not self.valid_id(run_id) or not self.valid_id(assignment_id):
            return (None, None)
        path = self.intent_path(run_id)
        if not path.is_file():
            return (None, None)
        try:
            intent = self.load_document(path)
        except (OSError, ValueError, TypeError) as exc:
            return (None, f'journal unreadable: {exc}')
        error = self.validate(intent, run, assignment, path)
        return (intent, None) if error is None else (None, error)
