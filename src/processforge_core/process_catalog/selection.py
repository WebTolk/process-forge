"""Existing ProcessSelectionService responsibilities with explicit operation dependencies."""
from __future__ import annotations

import copy
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable


from typing import Protocol


class ResolvedDefinitionView(Protocol):
    process: dict[str, Any]


@dataclass(frozen=True, kw_only=True)
class ProcessSelectionService:
    project_root: Path = field(repr=False, compare=False)
    stable_ids: Callable[[Any], list[str]] = field(repr=False, compare=False)
    resolve_definition: Callable[[Path, str], ResolvedDefinitionView] = field(repr=False, compare=False)
    blocked: Callable[..., dict[str, Any]] = field(repr=False, compare=False)
    candidates: Callable[..., list[dict[str, Any]]] = field(repr=False, compare=False)

    def select(self, selection: dict[str, Any], requested: str) -> tuple[str, dict[str, Any]]:
        allowed = self.stable_ids(selection.get('allowed'))
        if requested:
            if requested not in allowed:
                try:
                    self.resolve_definition(self.project_root, requested)
                except (OSError, SystemExit, ValueError):
                    return ('', self.blocked('process_not_found', process_id=requested))
                return ('', self.blocked('process_not_allowed', process_id=requested, allowed_processes=allowed))
            return (requested, {})
        if len(allowed) == 1:
            return (allowed[0], {})
        default = str(selection.get('default') or '').strip()
        return ('', self.blocked('process_choice_required', action='process_choice_required', default_process=default if default in allowed else '', candidates=self.candidates(allowed, default=default)))

    def process_candidates(self, process_ids: list[str], *, default: str='') -> list[dict[str, Any]]:
        candidates: list[dict[str, Any]] = []
        for process_id in process_ids:
            try:
                process = self.resolve_definition(self.project_root, process_id).process
            except (OSError, SystemExit, ValueError):
                candidates.append({'id': process_id, 'title': process_id, 'purpose': 'Process definition unavailable.', 'expected_result': '', 'default': process_id == default})
                continue
            candidates.append({'id': str(process.get('id') or process_id), 'title': str(process.get('name') or process_id), 'purpose': str(process.get('purpose') or process.get('description') or ''), 'expected_result': str(process.get('expected_result') or ''), 'default': str(process.get('id') or process_id) == default})
        return candidates
