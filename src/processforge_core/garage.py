"""Garage-level project context, search, and resolve services."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .ports import ProjectSnapshotReadPort
from .common.request_scope import scoped_request
from .resources.access import ResourceSearchService
from .project.snapshot import load_snapshot
from .resources.snapshot import resource_selection_summary, snapshot_with_resolved_search_roots


def diagnostics_from_check(check: dict[str, Any], search: dict[str, Any], mode: dict[str, Any] | None = None) -> list[dict[str, str]]:
    diagnostics: list[dict[str, str]] = []
    if check.get("status") not in {"fresh", "fresh_with_updates"}:
        diagnostics.append({"code": "context_not_fresh", "severity": "blocked", "message": str(check.get("recommended_action") or "refresh required")})
    if search.get("status") == "empty":
        diagnostics.append({"code": "search_corpus_empty", "severity": "warn", "message": "No authorized searchable documents are indexed."})
    elif search.get("status") in {"stale", "blocked"}:
        diagnostics.append({"code": str(search.get("reason") or "search_not_ready"), "severity": "blocked", "message": "Search is not ready."})
    for blocker in (mode or {}).get("blockers", []):
        if isinstance(blocker, dict):
            diagnostics.append({"code": str(blocker.get("code") or "mode_blocker"), "severity": "blocked", "message": str(blocker.get("message") or "")})
    return diagnostics


def selected_process_id(project_root: Path, core: Any) -> str:
    manifest = core.load_yaml_document(core.locate_flow_root(project_root) / "process-forge.yaml")
    process_id = str(manifest.get("process") or "").strip()
    return process_id or "task-batch-execution"


def resolve_process(project_root: Path, process_id: str, core: Any) -> dict[str, Any]:
    try:
        definition = core.resolve_process_definition(project_root, process_id)
        return definition.process
    except Exception:
        return {"id": process_id, "stages": []}


def valid_stages(process: dict[str, Any]) -> list[str]:
    return [str(item.get("id") or "") for item in process.get("stages", []) if isinstance(item, dict) and str(item.get("id") or "")]


def stage_obligations(process: dict[str, Any], stage_id: str) -> list[dict[str, Any]]:
    for stage in process.get("stages", []) if isinstance(process.get("stages"), list) else []:
        if isinstance(stage, dict) and str(stage.get("id") or "") == stage_id:
            return stage.get("automation_bindings") if isinstance(stage.get("automation_bindings"), list) else []
    return []


def unique_id(root: Path, seed: str) -> str:
    base = "-".join(str(seed or "work").lower().split())[:72].strip("-") or "work"
    candidate = base
    index = 2
    while (root / candidate).exists() or (root / f"{candidate}.yaml").exists():
        suffix = f"-{index}"
        candidate = base[: 72 - len(suffix)] + suffix
        index += 1
    return candidate


