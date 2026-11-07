"""Garage-level project context, search, and resolve services."""

from __future__ import annotations

import hashlib as hashlib
from dataclasses import dataclass as dataclass
from dataclasses import field as field
from pathlib import Path
from typing import Any

from .common.request_scope import scoped_request as scoped_request
from .ports import ProjectSnapshotReadPort as ProjectSnapshotReadPort
from .project.snapshot import load_snapshot as load_snapshot
from .resources.access import ResourceSearchService as ResourceSearchService
from .resources.snapshot import (
    resource_selection_summary as resource_selection_summary,
)
from .resources.snapshot import (
    snapshot_with_resolved_search_roots as snapshot_with_resolved_search_roots,
)


def diagnostics_from_check(
    check: dict[str, Any], search: dict[str, Any], mode: dict[str, Any] | None = None
) -> list[dict[str, Any]]:
    diagnostics: list[dict[str, Any]] = []
    if check.get("status") not in {"fresh", "fresh_with_updates"}:
        diagnostics.append(
            {
                "code": "context_not_fresh",
                "severity": "blocked",
                "message": str(check.get("recommended_action") or "refresh required"),
            }
        )
    if search.get("status") == "empty":
        diagnostics.append(
            {
                "code": "search_corpus_empty",
                "severity": "warn",
                "message": "No authorized searchable documents are indexed.",
            }
        )
    elif search.get("status") in {"stale", "blocked"}:
        diagnostics.append(
            {
                "code": str(search.get("reason") or "search_not_ready"),
                "severity": "blocked",
                "message": "Search is not ready.",
            }
        )
    for blocker in (mode or {}).get("blockers", []):
        if isinstance(blocker, dict):
            diagnostics.append(
                {
                    "code": str(blocker.get("code") or "mode_blocker"),
                    "severity": "blocked",
                    "message": str(blocker.get("message") or ""),
                }
            )
    temporary = check.get("temporary_files")
    if isinstance(temporary, dict):
        notification = bool(temporary.get("notification"))
        diagnostics.append(
            {
                "code": "temporary_files_status",
                "severity": "warn" if notification else "info",
                "message": (
                    "Old-file candidates observed; age does not authorize deletion."
                    if notification
                    else f"Temporary-files observation: {temporary.get('status', 'unknown')}."
                ),
                "temporary_files": temporary,
            }
        )
    return diagnostics


def selected_process_id(project_root: Path, core: Any) -> str:
    manifest = core.load_yaml_document(
        core.locate_flow_root(project_root) / "process-forge.yaml"
    )
    process_id = str(manifest.get("process") or "").strip()
    return process_id or "task-batch-execution"


def resolve_process(project_root: Path, process_id: str, core: Any) -> dict[str, Any]:
    try:
        definition = core.resolve_process_definition(project_root, process_id)
        return definition.process
    except Exception:
        return {"id": process_id, "stages": []}


def valid_stages(process: dict[str, Any]) -> list[str]:
    return [
        str(item.get("id") or "")
        for item in process.get("stages", [])
        if isinstance(item, dict) and str(item.get("id") or "")
    ]


def stage_obligations(process: dict[str, Any], stage_id: str) -> list[dict[str, Any]]:
    for stage in (
        process.get("stages", []) if isinstance(process.get("stages"), list) else []
    ):
        if isinstance(stage, dict) and str(stage.get("id") or "") == stage_id:
            bindings = stage.get("automation_bindings")
            return bindings if isinstance(bindings, list) else []
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
