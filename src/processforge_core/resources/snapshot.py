"""Existing resource snapshot selection and private navigation."""

from __future__ import annotations

import copy
from pathlib import Path
from typing import Any


def snapshot_with_resolved_search_roots(project_root: Path, snapshot: dict[str, Any], workplace_root: Path, core: Any) -> dict[str, Any]:
    runtime_snapshot = copy.deepcopy(snapshot)
    resources = runtime_snapshot.get("local_search_resources") if isinstance(runtime_snapshot.get("local_search_resources"), list) else []
    for resource in resources:
        if not isinstance(resource, dict) or not isinstance(resource.get("path_ref"), dict):
            continue
        resolution = resolve_garage_path_ref(project_root, resource["path_ref"], workplace_root, core)
        if resolution.get("status") == "resolved" and resolution.get("path"):
            resource["content_roots"] = [str(resolution["path"])]
    return runtime_snapshot


def resolve_garage_path_ref(project_root: Path, path_ref: dict[str, Any], workplace_root: Path, core: Any) -> dict[str, Any]:
    resolution = core.resolve_workspace_path_ref(project_root, path_ref, workplace_manifest=workplace_root / "workplace.yaml")
    if resolution.get("status") == "resolved":
        return resolution
    package_id = str(path_ref.get("package") or "")
    relative_path = str(path_ref.get("relative_path") or "").strip()
    if not package_id.startswith("project."):
        return resolution
    base = core.locate_flow_root(project_root)
    candidate = (base / relative_path).resolve() if relative_path else base.resolve()
    try:
        candidate.relative_to(base.resolve())
    except ValueError:
        return {"status": "unresolved", "reason": "invalid_path_ref: relative_path escapes project flow root"}
    return {"status": "resolved" if candidate.exists() else "missing", "path": str(candidate)}


def selected_resource(snapshot: dict[str, Any], resource_id: str) -> dict[str, Any]:
    candidates: list[Any] = []
    resolved = snapshot.get("resolved") if isinstance(snapshot.get("resolved"), dict) else {}
    for key in ("knowledge_resources",):
        if isinstance(resolved.get(key), list):
            candidates.extend(resolved[key])
    if isinstance(snapshot.get("local_search_resources"), list):
        candidates.extend(snapshot["local_search_resources"])
    for item in candidates:
        if not isinstance(item, dict):
            continue
        ids = {str(item.get("id") or ""), str(item.get("resource_id") or ""), str(item.get("instance_id") or "")}
        if resource_id in ids:
            return item
    return {}


def resource_selection_summary(snapshot: dict[str, Any]) -> dict[str, Any]:
    selection = snapshot.get("resource_selection") if isinstance(snapshot.get("resource_selection"), dict) else {}
    resolved = snapshot.get("resolved") if isinstance(snapshot.get("resolved"), dict) else {}
    selected = resolved.get("knowledge_resources") if isinstance(resolved.get("knowledge_resources"), list) else []
    preferred = [
        {
            "id": str(item.get("id") or ""),
            "kind": str(item.get("kind") or ""),
            "version": str(item.get("resolved_version") or item.get("resolved_generation") or ""),
            "reason": str((item.get("selection") or {}).get("reason") or ""),
        }
        for item in selected
        if isinstance(item, dict)
    ]
    return {
        "mode": str(selection.get("mode") or "snapshot"),
        "available_count": int(selection.get("available_count") or len(resolved.get("available_knowledge_resources") or [])),
        "selected_count": int(selection.get("selected_count") or len(preferred)),
        "target_versions": selection.get("target_versions") if isinstance(selection.get("target_versions"), list) else [],
        "preferred": preferred,
    }


def add_private_navigation(payload: dict[str, Any], runtime_snapshot: dict[str, Any]) -> None:
    resources = runtime_snapshot.get("local_search_resources") if isinstance(runtime_snapshot.get("local_search_resources"), list) else []
    by_id = {str(item.get("id") or item.get("resource_id") or ""): item for item in resources if isinstance(item, dict)}
    for match in payload.get("results", []):
        if not isinstance(match, dict):
            continue
        resource = by_id.get(str(match.get("resource_id") or ""))
        roots = resource.get("content_roots") if isinstance(resource, dict) and isinstance(resource.get("content_roots"), list) else []
        for raw_root in roots:
            root = Path(str(raw_root)).resolve()
            candidate = (root / str(match.get("canonical_path") or "")).resolve() if root.is_dir() else root
            try:
                candidate.relative_to(root if root.is_dir() else candidate)
            except ValueError:
                continue
            if candidate.is_file():
                match["local_path"] = str(candidate)
                match["navigation"] = "private_runtime_authorized"
                break
