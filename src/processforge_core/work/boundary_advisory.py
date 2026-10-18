"""Existing WorkBoundaryAdvisoryService responsibilities with explicit operation dependencies."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

from ..common.paths import rel
from ..common.yaml_io import _parse_simple_yaml
from ..documents.reader import YamlDocumentReader


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


@dataclass(frozen=True)
class FreshSessionBoundaryReadService:
    project_root: Path
    documents: YamlDocumentReader = field(default_factory=lambda: YamlDocumentReader(_parse_simple_yaml))
    relative_path: Callable[[Path, Path], str] = rel

    def read(self, work: dict[str, Any]) -> dict[str, Any]:
        """Return the newest usable completed Work boundary, never an older one."""
        if work.get("governed"):
            return {}
        flow_root = self.project_root / ".pf"
        candidates: list[tuple[str, dict[str, Any], Path]] = []
        for run_path in (flow_root / "runs").glob("*/run.yaml"):
            run = self.documents.load(run_path)
            if str(run.get("status") or "") != "completed":
                continue
            artifacts = run.get("final_artifacts") if isinstance(run.get("final_artifacts"), list) else []
            handoff = next((str(item) for item in artifacts if str(item).endswith("-handoff.md")), "")
            if not handoff or not (self.project_root / handoff).is_file():
                continue
            candidates.append((str(run.get("updated_at") or run.get("created_at") or ""), run, self.project_root / handoff))
        if not candidates:
            return {}
        _timestamp, run, handoff_path = max(candidates, key=lambda item: item[0])
        pin = run.get("process_execution") if isinstance(run.get("process_execution"), dict) else {}
        previous_process = str(run.get("process") or "")
        allowed_processes = pin.get("allowed_processes") if isinstance(pin.get("allowed_processes"), list) else []
        available = []
        for value in allowed_processes:
            process_id = str(value or "").strip()
            if process_id and process_id != previous_process and process_id not in available:
                available.append(process_id)
        definition = pin.get("definition") if isinstance(pin.get("definition"), dict) else {}
        routed = [str(item.get("to_process") or item.get("target_process") or "") for item in definition.get("process_transitions", []) if isinstance(item, dict)]
        routes_path = flow_root / "process-routes.yaml"
        if routes_path.is_file():
            routes = self.documents.load(routes_path).get("routes", [])
            routed.extend(str(item.get("to_process") or item.get("target_process") or "") for item in routes if isinstance(item, dict) and str(item.get("from_process") or "") == previous_process)
        recommended = next((item for item in routed if item in available), "")
        # The newest completed boundary is authoritative. If it has no route, do
        # not resurrect an older handoff merely because that one had a suggestion.
        if not recommended:
            return {}
        summary = next((str(item) for item in run.get("final_artifacts", []) if str(item).endswith("summary.md")), "")
        return {
            "previous_run_id": str(run.get("id") or ""),
            "previous_process_id": previous_process,
            "handoff_path": self.relative_path(handoff_path, self.project_root),
            "summary_path": summary,
            "next": {"recommended_process": recommended, "available_processes": available},
            "session_continuity": {"recommendation": "fresh", "reason": "process_boundary"},
        }
