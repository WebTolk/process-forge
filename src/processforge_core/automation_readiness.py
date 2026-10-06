"""Existing AutomationReadinessService responsibilities with explicit operation dependencies."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable



@dataclass(frozen=True, kw_only=True)
class AutomationReadinessService:
    project_root: Path = field(repr=False, compare=False)
    has_output_checks: Callable[[], bool] = field(repr=False, compare=False)
    output_checks: Callable[[Path, dict[str, Any]], Any] = field(repr=False, compare=False)
    has_fingerprint: Callable[[], bool] = field(repr=False, compare=False)
    fingerprint: Callable[[Path, dict[str, Any]], Any] = field(repr=False, compare=False)
    has_event_paths: Callable[[], bool] = field(repr=False, compare=False)
    event_paths: Callable[[Path], tuple[Path, Any]] = field(repr=False, compare=False)
    latest_event: Callable[[str, set[str]], dict[str, Any] | None] = field(repr=False, compare=False)

    def states(self, process: dict[str, Any], stage: dict[str, Any], assignment: dict[str, Any]) -> list[dict[str, Any]]:
        bindings = stage.get('automation_bindings') if isinstance(stage.get('automation_bindings'), list) else []
        if not bindings and isinstance(stage.get('technical_obligations'), list):
            bindings = stage['technical_obligations']
        states: list[dict[str, Any]] = []
        for binding in bindings:
            if not isinstance(binding, dict):
                continue
            projector = str(binding.get('projector') or '')
            status = 'unsupported'
            details: dict[str, Any] = {}
            if projector == 'required-output-readiness' and self.has_output_checks():
                failures = [item.message for item in self.output_checks(self.project_root, assignment) if str(getattr(item, 'level', '')) == 'FAIL']
                status = 'ready' if not failures else 'blocked'
                details['failures'] = failures
            elif projector == 'verification-state':
                verification = binding.get('verification') if isinstance(binding.get('verification'), dict) else {}
                passed_event = str(verification.get('passed_event') or '')
                failed_event = str(verification.get('failed_event') or '')
                event = self.latest_event(str(assignment.get('id') or ''), {passed_event, failed_event})
                event_type = str(event.get('event_type') or '') if event else ''
                status = 'ready' if event_type == passed_event else 'blocked' if event_type == failed_event else 'missing'
                if status == 'ready' and self.has_fingerprint():
                    event_data = event.get('data') if isinstance(event.get('data'), dict) else {}
                    if str(event_data.get('verification_fingerprint') or '') != self.fingerprint(self.project_root, assignment):
                        status = 'stale'
                details['event_type'] = event_type
            states.append({'id': str(binding.get('id') or projector or 'obligation'), 'projector': projector, 'gate': str(binding.get('gate') or ''), 'status': status, **details})
        return states

    def latest_assignment_event(self, assignment_id: str, event_types: set[str]) -> dict[str, Any] | None:
        if not event_types or not self.has_event_paths():
            return None
        events_path, _outbox = self.event_paths(self.project_root)
        if not events_path.is_file():
            return None
        for line in reversed(events_path.read_text(encoding='utf-8', errors='replace').splitlines()):
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue
            assignment = event.get('assignment') if isinstance(event.get('assignment'), dict) else {}
            if str(event.get('event_type') or '') in event_types and (str(assignment.get('id') or '') == assignment_id or str(event.get('subject') or '') == assignment_id):
                return event
        return None
