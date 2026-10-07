"""Existing WorkBoundaryAdvisoryService responsibilities with explicit operation dependencies."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable


@dataclass(frozen=True, kw_only=True)
class WorkBoundaryAdvisoryService:
    flow_root: Callable[[], Path] = field(repr=False, compare=False)
    stable_ids: Callable[[Any], list[str]] = field(repr=False, compare=False)
    load_document: Callable[[Path], dict[str, Any]] = field(repr=False, compare=False)

    def advisory(self, process: dict[str, Any], run: dict[str, Any]) -> dict[str, Any]:
        pin = run.get('process_execution') if isinstance(run.get('process_execution'), dict) else {}
        current = str(run.get('process') or '')
        available = [item for item in self.stable_ids(pin.get('allowed_processes')) if item != current]
        declared = process.get('process_transitions') if isinstance(process.get('process_transitions'), list) else []
        routed = [str(item.get('to_process') or item.get('target_process') or '') for item in declared if isinstance(item, dict)]
        route_path = self.flow_root() / 'process-routes.yaml'
        routes = self.load_document(route_path).get('routes', []) if route_path.exists() else []
        routed.extend((str(item.get('to_process') or item.get('target_process') or '') for item in routes if isinstance(item, dict) and str(item.get('from_process') or '') == current))
        recommended = next((item for item in routed if item in available), '')
        next_work: dict[str, Any] = {'available_processes': available}
        if recommended:
            next_work['recommended_process'] = recommended
        result: dict[str, Any] = {'next': next_work, 'session_continuity': {'recommendation': 'auto', 'reason': 'process_boundary'}}
        handoff = next((str(path) for path in self.stable_ids(run.get('final_artifacts')) if path.endswith('-handoff.md')), '')
        if handoff:
            result['handoff'] = {'path': handoff}
        return result
