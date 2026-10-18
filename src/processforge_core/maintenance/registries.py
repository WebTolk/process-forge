"""Live update subject discovery and registry lookup through Core owners."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ..common.ids import safe_id
from ..resources.project_packages import ProjectPackageCatalogReader
from ..resources.snapshot import WorkspacePathReferenceReader
from .documents import UpdateDocumentReader
from .sites import UpdateSitePolicy
from .source_contracts import UPDATE_SUBJECT_TYPES


class UpdateRegistryReader:
    """Read current workplace update records without retaining document state."""

    def __init__(self, distribution_root: Path) -> None:
        self.distribution_root = distribution_root
        self.documents = UpdateDocumentReader(distribution_root)
        self.packages = ProjectPackageCatalogReader(distribution_root)
        self.sites = UpdateSitePolicy()

    def _references(self, workplace_root: Path) -> WorkspacePathReferenceReader:
        return WorkspacePathReferenceReader(workplace_root, workplace_root, inputs=self.documents.inputs)

    def entities(self, workplace_root: Path) -> list[dict[str, Any]]:
        manifest = workplace_root / "workplace.yaml"
        records: list[dict[str, Any]] = []
        seen: set[Path] = set()

        package_roots = self.packages.workplace_root_paths(manifest if manifest.is_file() else None)
        if not package_roots:
            package_roots = [self._references(workplace_root).path_resolution_to_path(self._references(workplace_root).workplace_path_resolution(workplace_root, "${PF_WORKPLACE}/packages"))]
        for root in package_roots:
            for path in self.documents.manifest_candidates(root, ["*.yaml", "*.yml", "*/package.yaml", "*/package.yml"]):
                if path in seen:
                    continue
                seen.add(path)
                data = self.documents.yaml(path)
                if not data.get("id"):
                    continue
                subject_type = str(data.get("type") or "knowledge_package")
                if subject_type not in UPDATE_SUBJECT_TYPES:
                    subject_type = "knowledge_package"
                records.append(
                    {
                        "type": subject_type,
                        "id": str(data.get("id")),
                        "scope": str(data.get("scope") or "global"),
                        "version": str(data.get("version") or ""),
                        "manifest_path": path,
                        "data": data,
                    }
                )

        process_root = self._references(workplace_root).path_resolution_to_path(self._references(workplace_root).workplace_path_resolution(workplace_root, "${PF_WORKPLACE}/processes"))
        for path in self.documents.manifest_candidates(process_root, ["*.yaml", "*.yml"]):
            data = self.documents.yaml(path)
            if data.get("id"):
                subject_type = str(data.get("type") or "process_definition")
                if subject_type not in UPDATE_SUBJECT_TYPES:
                    subject_type = "process_definition"
                records.append(
                    {
                        "type": subject_type,
                        "id": str(data.get("id")),
                        "scope": "global",
                        "version": str(data.get("version") or ""),
                        "manifest_path": path,
                        "data": data,
                    }
                )

        template_roots = self.documents.registry_paths(workplace_root, "templates.yaml", "template_roots")
        if not template_roots:
            template_roots = [self._references(workplace_root).path_resolution_to_path(self._references(workplace_root).workplace_path_resolution(workplace_root, "${PF_TEMPLATES}"))]
        for root in template_roots:
            for path in self.documents.manifest_candidates(root, ["*.yaml", "*.yml", "*/template.yaml", "*/template.yml"]):
                data = self.documents.yaml(path)
                if data.get("id"):
                    subject_type = str(data.get("type") or "reusable_template")
                    if subject_type not in UPDATE_SUBJECT_TYPES:
                        subject_type = "reusable_template"
                    records.append(
                        {
                            "type": subject_type,
                            "id": str(data.get("id")),
                            "scope": str(data.get("scope") or "global"),
                            "version": str(data.get("version") or ""),
                            "manifest_path": path,
                            "data": data,
                        }
                    )

        platform_roots = self.documents.registry_paths(workplace_root, "platform-contract-roots.yaml", "platform_contract_roots")
        if not platform_roots:
            platform_roots = [
                self._references(workplace_root).path_resolution_to_path(self._references(workplace_root).workplace_path_resolution(workplace_root, "${PF_PLATFORM_CONTRACTS}")),
                self._references(workplace_root).path_resolution_to_path(self._references(workplace_root).workplace_path_resolution(workplace_root, "${PF_WORKPLACE}/platforms")),
            ]
        for root in platform_roots:
            for path in self.documents.manifest_candidates(root, ["*.yaml", "*.yml", "*/platform.yaml", "*/platform.yml", "*/platform-contract.yaml", "*/platform-contract.yml"]):
                data = self.documents.yaml(path)
                if data.get("id") and data.get("type") == "platform_contract":
                    records.append(
                        {
                            "type": "platform_contract",
                            "id": str(data.get("id")),
                            "scope": "global",
                            "version": str(data.get("version") or ""),
                            "manifest_path": path,
                            "data": data,
                        }
                    )

        tools_path = workplace_root / "registries" / "tools.yaml"
        tools_data = self.documents.yaml(tools_path)
        for entry in tools_data.get("tools", []) if isinstance(tools_data.get("tools"), list) else []:
            if isinstance(entry, dict) and entry.get("id"):
                subject_type = str(entry.get("type") or "tool_definition")
                if subject_type not in UPDATE_SUBJECT_TYPES:
                    subject_type = "tool_definition"
                records.append(
                    {
                        "type": subject_type,
                        "id": str(entry.get("id")),
                        "scope": str(entry.get("scope") or "global"),
                        "version": str(entry.get("version") or ""),
                        "manifest_path": tools_path,
                        "data": entry,
                    }
                )

        mcp_path = workplace_root / "registries" / "mcp.yaml"
        mcp_data = self.documents.yaml(mcp_path)
        for entry in mcp_data.get("mcp_servers", []) if isinstance(mcp_data.get("mcp_servers"), list) else []:
            if isinstance(entry, dict) and entry.get("id"):
                records.append(
                    {
                        "type": "mcp_definition",
                        "id": str(entry.get("id")),
                        "scope": str(entry.get("scope") or "global"),
                        "version": str(entry.get("version") or ""),
                        "manifest_path": mcp_path,
                        "data": entry,
                    }
                )
        return records

    def overrides(self, workplace_root: Path) -> dict[str, dict[str, Any]]:
        path = self.documents.overrides_path(workplace_root)
        data = self.documents.yaml(path)
        overrides = data.get("overrides") if isinstance(data.get("overrides"), list) else []
        result: dict[str, dict[str, Any]] = {}
        for item in overrides:
            if not isinstance(item, dict):
                continue
            key = item.get("site_id") if isinstance(item.get("site_id"), str) else None
            subject = item.get("subject") if isinstance(item.get("subject"), dict) else {}
            update_site_id = item.get("update_site_id") or item.get("source_id")
            if not key and isinstance(update_site_id, str) and subject.get("type") and subject.get("id"):
                key = self.sites.stable_key(str(subject.get("type")), str(subject.get("id")), update_site_id)
            if not key and isinstance(item.get("subject_id"), str):
                key = str(item.get("subject_id"))
            if not key and isinstance(item.get("subject"), dict) and subject.get("type") and subject.get("id"):
                key = f"{subject.get('type')}:{subject.get('id')}"
            if key:
                result[key] = item
        return result

    def installed_subjects(self, workplace_root: Path) -> dict[tuple[str, str], dict[str, Any]]:
        data = self.documents.yaml(self.documents.installed_registry(workplace_root))
        result: dict[tuple[str, str], dict[str, Any]] = {}
        for subject in data.get("subjects", []) if isinstance(data.get("subjects"), list) else []:
            if isinstance(subject, dict) and isinstance(subject.get("type"), str) and isinstance(subject.get("id"), str):
                result[(str(subject["type"]), str(subject["id"]))] = subject
        return result

    def install_path(self, workplace_root: Path, candidate: dict[str, Any]) -> Path:
        policy = candidate.get("update_policy") if isinstance(candidate.get("update_policy"), dict) else {}
        install_path = policy.get("install_path")
        if isinstance(install_path, str) and install_path.strip():
            return self._references(workplace_root).path_resolution_to_path(self._references(workplace_root).workplace_path_resolution(workplace_root, install_path))
        installed = self.installed_subjects(workplace_root)
        subject = candidate.get("subject") if isinstance(candidate.get("subject"), dict) else {}
        installed_subject = installed.get((str(subject.get("type")), str(subject.get("id"))), {})
        if isinstance(installed_subject.get("install_path"), str) and str(installed_subject["install_path"]).strip():
            return self._references(workplace_root).path_resolution_to_path(self._references(workplace_root).workplace_path_resolution(workplace_root, str(installed_subject["install_path"])))
        return workplace_root / "packages" / safe_id(str(subject.get("id") or "package"))

    def installed_versions(self, workplace_root: Path) -> dict[tuple[str, str], str]:
        data = self.documents.yaml(self.documents.installed_registry(workplace_root))
        subjects = data.get("subjects") if isinstance(data.get("subjects"), list) else []
        result: dict[tuple[str, str], str] = {}
        for subject in subjects:
            if not isinstance(subject, dict):
                continue
            subject_type = subject.get("type")
            subject_id = subject.get("id")
            version = subject.get("version")
            if isinstance(subject_type, str) and isinstance(subject_id, str) and isinstance(version, str) and version:
                result[(subject_type, subject_id)] = version
        return result
