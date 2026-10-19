"""Existing project type, mode and default initialization inputs."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ..common.ids import safe_id


PROCESSFORGE_CORE_PROJECT_TYPES = {"processforge-development", "processforge-core-development"}
META_PROJECT_TYPES = {"agent-workspace", "brownfield-workspace", "meta-workspace"}


class ProjectInitializationInputs:
    def types_from_manifest(self, manifest_data: dict[str, Any]) -> list[str]:
        project = manifest_data.get("project") if isinstance(manifest_data.get("project"), dict) else {}
        raw_type = project.get("type") or project.get("types") or project.get("project_type")
        if isinstance(raw_type, str):
            return [safe_id(raw_type)]
        if isinstance(raw_type, list):
            return [safe_id(str(item)) for item in raw_type if item]
        return []

    def allows_core(self, manifest_data: dict[str, Any]) -> bool:
        return bool(set(self.types_from_manifest(manifest_data)).intersection(PROCESSFORGE_CORE_PROJECT_TYPES))

    def is_meta_workspace(self, manifest_data: dict[str, Any]) -> bool:
        return bool(set(self.types_from_manifest(manifest_data)).intersection(META_PROJECT_TYPES))

    def mode(self, project_root: Path, answers: dict[str, Any]) -> str:
        project_answers = answers.get("project", {}) if isinstance(answers.get("project"), dict) else {}
        requested = str(project_answers.get("mode") or "auto")
        if requested in {"greenfield", "brownfield"}:
            return requested
        if not project_root.exists():
            return "greenfield"
        visible = [path for path in project_root.iterdir() if path.name not in {".git", ".idea", ".serena"}]
        return "greenfield" if not visible else "brownfield"

    def defaults(self, project_root: Path, answers: dict[str, Any], detected: dict[str, Any]) -> dict[str, Any]:
        project_answers = answers.get("project", {}) if isinstance(answers.get("project"), dict) else {}
        project_id = safe_id(str(project_answers.get("id") or project_root.name), "project")
        project_name = str(project_answers.get("name") or project_root.name or "ProcessForge Project")
        detected_kind = detected["project_kind"][0] if detected["project_kind"] else "unknown"
        project_type = str(project_answers.get("type") or project_answers.get("type_hint") or detected_kind)
        if project_type == "auto":
            project_type = detected_kind
        return {"id": project_id, "name": project_name, "type": project_type}
