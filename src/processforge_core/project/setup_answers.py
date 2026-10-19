"""Existing Workplace defaults and guided-answer transformations."""

from __future__ import annotations

from pathlib import Path
import platform
from typing import Any

from ..common.ids import safe_id
from ..common.values import as_list
from ..documents.answers import AnswersDocumentReader
from .coordination import ProjectCoordinationReader


class WorkplaceSetupAnswers:
    """Prepare the existing answer mappings without retaining supplied data."""

    def __init__(self) -> None:
        self.coordination = ProjectCoordinationReader()

    def workplace_defaults(self, root: Path, answers: dict[str, Any]) -> dict[str, Any]:
        workplace_answers = answers.get("workplace", {}) if isinstance(answers.get("workplace"), dict) else {}
        paths_answers = answers.get("paths", {}) if isinstance(answers.get("paths"), dict) else {}
        os_name = str(workplace_answers.get("os") or platform.system().lower() or "unknown").lower()
        return {
            "id": safe_id(str(workplace_answers.get("id") or root.name or "workplace"), "workplace"),
            "name": str(workplace_answers.get("name") or root.name or "ProcessForge Workplace"),
            "type": str(workplace_answers.get("type") or "workstation"),
            "os": os_name,
            "root": str(paths_answers.get("root") or root),
        }

    def dict_entries_from_answers(self, container: Any, item_label: str, scope: str) -> list[dict[str, Any]]:
        if not isinstance(container, dict):
            return []
        entries = []
        for key, value in container.items():
            if value in (None, "", "<path>"):
                continue
            entries.append(
                {
                    "id": safe_id(str(key), item_label),
                    "label": str(key).replace("_", " ").title(),
                    "path": str(value),
                    "scope": scope,
                    "status": "available",
                }
            )
        return entries

    def default_guided_workplace_answers(self, workplace: Path, session_id: str) -> dict[str, Any]:
        return {
            "schema_version": 1,
            "session": {"id": safe_id(session_id, "setup-session"), "status": "draft"},
            "machine_layout": {
                "processforge_root": "${PROCESSFORGE_ROOT}",
                "workplace_path": "${PF_WORKPLACE}",
                "local_docs_path": "${PF_WORKPLACE}/knowledge",
                "project_roots": ["${PF_WORKPLACE}/projects"],
            },
            "agent_environment": {
                "tools": ["generic"],
                "instructions_targets": ["AGENTS.md"],
                "global_agents_policy": "bounded_processforge_section",
            },
            "device_discovery": {
                "enabled": "ask",
                "read_only": True,
                "broad_disk_scan": "only_when_allowed",
                "fallback_scope": [
                    "global AGENTS.md",
                    "configured skills root",
                    "configured docs root",
                    "configured platforms root",
                    "configured toolchains root",
                ],
                "outputs": [
                    "device-discovery-report.md",
                    "resource-candidates.yaml",
                    "auto-setup-proposal.md",
                ],
            },
            "privacy_safety": {
                "local_paths_private_only": True,
                "public_manifests_use_path_ref": True,
                "secret_handling": "store secret names only; never store secret values",
                "update_trust_policy": {
                    "require_https": True,
                    "require_sha256_for_download": True,
                    "require_sha256_for_install": True,
                },
            },
            "resources": {
                "knowledge_roots": [{"id": "local-docs", "path_ref": "${PF_WORKPLACE}/knowledge", "status": "available"}],
                "package_roots": [{"id": "global", "path_ref": "${PF_WORKPLACE}/packages", "default": True, "writable": True}],
                "tools": [],
                "mcp_servers": [],
                "templates": [],
            },
            "platform_contracts": {
                "policy": "neutral_or_explicit",
                "create": [],
                "notes": "Do not create real platform contracts unless the user explicitly defines them.",
            },
            "coordination": {"director_capability": False, "default_project_mode": "simple", "initialize_director_office": False},
            "first_project": {"onboard_now": False, "project_root": "", "project_type": "generic", "coordination_mode": "inherit", "suggested_run": "first-run"},
        }

    def merge_guided_answers(self, defaults: dict[str, Any], supplied: dict[str, Any]) -> dict[str, Any]:
        result = dict(defaults)
        for key, value in supplied.items():
            if isinstance(value, dict) and isinstance(result.get(key), dict):
                nested = dict(result[key])
                nested.update(value)
                result[key] = nested
            else:
                result[key] = value
        return result

    def load_guided_workplace_answers(self, session_dir: Path, answers_path: Path | None = None, *, workplace: Path | None = None, session_id: str = "default") -> dict[str, Any]:
        defaults = self.default_guided_workplace_answers(workplace or session_dir, session_id)
        existing = session_dir / "answers.yaml"
        source = answers_path if answers_path and answers_path.is_file() else existing if existing.is_file() else None
        supplied = AnswersDocumentReader().read(source) if source else {}
        return self.merge_guided_answers(defaults, supplied)

    def guided_answers_to_workplace_init_answers(self, workplace: Path, answers: dict[str, Any]) -> dict[str, Any]:
        machine = answers.get("machine_layout") if isinstance(answers.get("machine_layout"), dict) else {}
        discovery = answers.get("device_discovery") if isinstance(answers.get("device_discovery"), dict) else {}
        resources = answers.get("resources") if isinstance(answers.get("resources"), dict) else {}
        privacy = answers.get("privacy_safety") if isinstance(answers.get("privacy_safety"), dict) else {}
        coordination = answers.get("coordination") if isinstance(answers.get("coordination"), dict) else {}
        package_roots = {}
        for item in resources.get("package_roots", []) if isinstance(resources.get("package_roots"), list) else []:
            if isinstance(item, dict):
                package_roots[str(item.get("id") or "global")] = str(item.get("path_ref") or item.get("path") or "${PF_WORKPLACE}/packages")
        knowledge_roots = {}
        for item in resources.get("knowledge_roots", []) if isinstance(resources.get("knowledge_roots"), list) else []:
            if isinstance(item, dict):
                knowledge_roots[str(item.get("id") or "local-docs")] = str(item.get("path_ref") or item.get("path") or "${PF_WORKPLACE}/knowledge")
        processforge_root = str(machine.get("processforge_root") or "${PROCESSFORGE_ROOT}")
        discovery_enabled = str(discovery.get("enabled") or "ask").lower() in {"true", "yes", "enabled", "on"}
        return {
            "schema_version": 1,
            "setup_mode": "guided",
            "device_discovery": {
                "enabled": discovery_enabled,
                "read_only": bool(discovery.get("read_only", True)),
                "fallback_scope": [str(item) for item in as_list(discovery.get("fallback_scope"))],
                "approved_before_apply": False,
            },
            "workplace": {"id": safe_id(workplace.name or "workplace", "workplace"), "name": workplace.name or "ProcessForge Workplace"},
            "paths": {
                "root": str(machine.get("workplace_path") or workplace),
                "knowledge_roots": knowledge_roots,
                "package_roots": package_roots,
                "template_roots": {"global": "${PF_WORKPLACE}/reusable-templates"},
                "distributions": {"processforge": processforge_root},
            },
            "policies": {"shell_is_fallback": True, "local_paths_private_only": bool(privacy.get("local_paths_private_only", True))},
            "coordination": {
                "director_enabled": bool(coordination.get("director_capability", False)),
                "director_office_enabled": bool(coordination.get("initialize_director_office", False)),
                "default_project_mode": self.coordination.workplace_mode(coordination.get("default_project_mode", "simple")),
            },
        }
