"""Existing project scan policy and source inventory classification."""

from __future__ import annotations

import fnmatch
from pathlib import Path
from typing import Any

from ..common.paths import path_is_relative_to, rel
from ..resources.registries import WorkplaceRegistryReader
from ..work.context_documents import ContextContractInputs
from .initialization_inputs import PROCESSFORGE_CORE_PROJECT_TYPES, ProjectInitializationInputs


DEFAULT_SCAN_POLICY = {
    "enabled": True,
    "exclude_roles": ["distribution_root", "workplace_root", "knowledge_root", "runtime_root", "package_cache"],
    "default_excludes": ["**/.git/**", "**/.pf/runtime/**", "**/runtime/**", "**/dist/**", "**/build/**"],
    "allow_processforge_core_as_project": {
        "enabled": False,
        "requires_project_type": sorted(PROCESSFORGE_CORE_PROJECT_TYPES),
    },
}


class ProjectScanPolicy:
    """Keep the original scan decisions and ordered live inventory traversal."""

    def __init__(self) -> None:
        self.inputs = ContextContractInputs()
        self.initialization_inputs = ProjectInitializationInputs()

    def scan_policy_from_manifest(self, manifest_data: dict[str, Any]) -> dict[str, Any]:
        policy = dict(DEFAULT_SCAN_POLICY)
        configured = manifest_data.get("scan_policy") if isinstance(manifest_data.get("scan_policy"), dict) else {}
        if "enabled" in configured:
            policy["enabled"] = bool(configured.get("enabled"))
        if isinstance(configured.get("exclude_roles"), list):
            policy["exclude_roles"] = [str(item) for item in configured["exclude_roles"] if item]
        if isinstance(configured.get("default_excludes"), list):
            policy["default_excludes"] = [str(item) for item in configured["default_excludes"] if item]
        allow_core = configured.get("allow_processforge_core_as_project") if isinstance(configured.get("allow_processforge_core_as_project"), dict) else {}
        merged_allow_core = dict(DEFAULT_SCAN_POLICY["allow_processforge_core_as_project"])
        merged_allow_core.update(allow_core)
        policy["allow_processforge_core_as_project"] = merged_allow_core
        return policy

    def path_role_record(self, role: str, path: Path, project_root: Path, *, source: str, status: str = "available", path_id: str | None = None) -> dict[str, Any]:
        return {
            "role": role,
            "id": path_id or role,
            "path": rel(path.resolve(), project_root),
            "source": source,
            "status": status,
        }

    def project_path_roles(self, project_root: Path, distribution_root: Path | None, workplace_manifest: Path | None, manifest_data: dict[str, Any]) -> list[dict[str, Any]]:
        flow_root = self.inputs.locate_flow_root(project_root)
        roles: list[dict[str, Any]] = [
            self.path_role_record("project_root", project_root, project_root, source="project"),
            self.path_role_record("project_pf_root", flow_root, project_root, source="project"),
            self.path_role_record("runtime_root", flow_root / "runtime", project_root, source="project", status="available" if (flow_root / "runtime").exists() else "missing"),
        ]
        if distribution_root:
            roles.append(self.path_role_record("distribution_root", distribution_root, project_root, source="workplace" if workplace_manifest else "project", status="available" if distribution_root.exists() else "missing"))
        elif self.looks_like_processforge_distribution(project_root):
            roles.append(self.path_role_record("distribution_root", project_root, project_root, source="project", status="available"))
        if workplace_manifest:
            workplace_root = workplace_manifest.parent
            roles.append(self.path_role_record("workplace_root", workplace_root, project_root, source="local-config", status="available" if workplace_root.exists() else "missing"))
            roles.append(self.path_role_record("package_cache", workplace_root / "cache", project_root, source="workplace", status="available" if (workplace_root / "cache").exists() else "missing"))
            knowledge_roots = WorkplaceRegistryReader(inputs=self.inputs).load_workplace_registry(workplace_manifest, "knowledge_roots", "knowledge-roots.yaml")
            knowledge_entries = knowledge_roots.get("knowledge_roots") if isinstance(knowledge_roots, dict) else []
            if isinstance(knowledge_entries, list):
                for item in knowledge_entries:
                    if not isinstance(item, dict):
                        continue
                    raw_path = str(item.get("path") or item.get("path_ref") or "")
                    if not raw_path:
                        continue
                    knowledge_path = WorkplaceRegistryReader(inputs=self.inputs).resolve_registry_relative_path(workplace_root, raw_path, workplace_manifest)
                    roles.append(
                        self.path_role_record(
                            "knowledge_root",
                            knowledge_path,
                            project_root,
                            source="workplace-registry",
                            status="available" if knowledge_path.exists() else "missing",
                            path_id=str(item.get("id") or "knowledge-root"),
                        )
                    )
        for configured in manifest_data.get("knowledge_roots", []) if isinstance(manifest_data.get("knowledge_roots"), list) else []:
            if not isinstance(configured, dict):
                continue
            raw_path = str(configured.get("path") or "")
            if raw_path:
                path = Path(raw_path).expanduser()
                if not path.is_absolute():
                    path = (project_root / path).resolve()
                roles.append(self.path_role_record("knowledge_root", path, project_root, source="project-manifest", status="available" if path.exists() else "missing", path_id=str(configured.get("id") or "knowledge-root")))
        unique: list[dict[str, Any]] = []
        seen: set[tuple[str, str, str]] = set()
        for item in roles:
            key = (str(item["role"]), str(item["id"]), str(item["path"]))
            if key not in seen:
                seen.add(key)
                unique.append(item)
        return unique

    def project_source_inventory_exclusion(self, path: Path, project_root: Path, roles: list[dict[str, Any]], policy: dict[str, Any], manifest_data: dict[str, Any]) -> dict[str, Any] | None:
        rel_path = rel(path, project_root)
        for pattern in policy.get("default_excludes", []):
            if fnmatch.fnmatch(rel_path, str(pattern)) or fnmatch.fnmatch("/" + rel_path, str(pattern).removeprefix("**")):
                return {"reason": "default_exclude", "pattern": str(pattern)}
        exclude_roles = set(policy.get("exclude_roles", []))
        allow_pf_core = self.initialization_inputs.allows_core(manifest_data)
        for role in roles:
            role_name = str(role.get("role"))
            if role_name not in exclude_roles:
                continue
            role_path_text = str(role.get("path") or "")
            role_path = Path(role_path_text)
            if not role_path.is_absolute():
                role_path = (project_root / role_path).resolve()
            if not path_is_relative_to(path, role_path):
                continue
            if role_name == "distribution_root" and role_path.resolve() == project_root.resolve() and allow_pf_core:
                continue
            return {"reason": "excluded_role", "role": role_name, "role_id": role.get("id"), "role_path": rel(role_path, project_root)}
        return None

    def collect_project_source_inventory(self, project_root: Path, distribution_root: Path | None = None, workplace_manifest: Path | None = None, manifest_data: dict[str, Any] | None = None) -> dict[str, Any]:
        flow_root = self.inputs.locate_flow_root(project_root)
        if manifest_data is None:
            manifest_data = self.inputs.load_yaml_document(flow_root / "process-forge.yaml")
        policy = self.scan_policy_from_manifest(manifest_data)
        roles = self.project_path_roles(project_root, distribution_root, workplace_manifest, manifest_data)
        included: list[dict[str, Any]] = []
        excluded: list[dict[str, Any]] = []
        for path in sorted(item for item in project_root.rglob("*") if item.is_file()):
            exclusion = None if policy.get("enabled", True) else None
            if policy.get("enabled", True):
                exclusion = self.project_source_inventory_exclusion(path, project_root, roles, policy, manifest_data)
            record = {"path": rel(path, project_root)}
            if exclusion:
                excluded.append({**record, **exclusion})
            else:
                included.append(record)
        return {"scan_policy": policy, "path_roles": roles, "included": included, "excluded": excluded}

    @staticmethod
    def looks_like_processforge_distribution(path: Path) -> bool:
        root = path.resolve()
        return all(
            item.exists()
            for item in [
                root / "bin" / "pf.py",
                root / "tools" / "processforge.py",
                root / "schemas" / "process-definition.schema.json",
                root / "processes" / "core",
            ]
        )
