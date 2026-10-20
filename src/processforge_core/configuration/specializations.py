"""Existing specialization catalog reads through concrete Core owners."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ..common.paths import path_is_relative_to
from ..common.yaml_io import yaml_error
from ..maintenance.documents import UpdateDocumentReader
from ..project.metadata import ProjectMetadataReader
from ..resources.workplace_catalog import WorkplaceCatalogReader
from ..work.context_documents import ContextContractInputs


class SpecializationCatalogReader:
    """Read specialization registries and manifests without retaining documents."""

    def __init__(self, distribution_root: Path) -> None:
        self._update_document_reader = UpdateDocumentReader(distribution_root)
        self._inputs = ContextContractInputs()
        self._references = WorkplaceCatalogReader()

    def resource_id(self, raw: str) -> str:
        return raw if raw.startswith("specialization.") or "." in raw else f"specialization.{raw}"

    def registry_path(self, workplace_root: Path) -> Path:
        return self._update_document_reader.registry_file(workplace_root, "specializations", "specializations.yaml")

    def path_from_registry_entry(self, workplace_root: Path, entry: dict[str, Any], workplace_manifest: Path | None = None) -> Path | None:
        raw_path = entry.get("path")
        if not raw_path:
            return None
        manifest = workplace_manifest or (workplace_root / "workplace.yaml")
        specialization_root = self._references.resolve_registry_relative_path(
            workplace_root,
            "${PF_SPECIALIZATIONS}",
            manifest,
        )
        candidate = self._references.resolve_registry_relative_path(
            workplace_root,
            str(raw_path),
            manifest,
        )
        return self._references.contained_resource_path(
            specialization_root,
            candidate,
            "specialization",
        )

    def path_candidates(self, workplace_root: Path | None, specialization_id: str, project_root: Path | None = None) -> list[Path]:
        normalized_id = self._references.validate_resource_id(
            self.resource_id(specialization_id),
            "specialization",
        )
        candidates: list[Path] = []
        if workplace_root:
            registry = self._inputs.load_yaml_document(self.registry_path(workplace_root))
            entries = registry.get("specializations") if isinstance(registry, dict) else []
            if isinstance(entries, list):
                for entry in entries:
                    if not isinstance(entry, dict) or str(entry.get("status", "available")) in {"missing", "disabled"}:
                        continue
                    entry_id = self.resource_id(str(entry.get("id") or ""))
                    if entry_id == normalized_id:
                        path = self.path_from_registry_entry(workplace_root, entry, workplace_root / "workplace.yaml")
                        if path:
                            candidates.append(path)
            for root in [workplace_root / "specializations", workplace_root / "specializations" / "user", workplace_root / "specializations" / "custom"]:
                candidates.extend(
                    [
                        self._references.contained_resource_path(root, root / f"{normalized_id}.yaml", "specialization"),
                        self._references.contained_resource_path(
                            root,
                            root / f"{normalized_id.removeprefix('specialization.')}.yaml",
                            "specialization",
                        ),
                    ]
                )
        if project_root:
            flow_root = ProjectMetadataReader(project_root).flow_root()
            for root in [flow_root / "specializations", flow_root / "specializations" / "user", flow_root / "specializations" / "custom"]:
                candidates.extend(
                    [
                        self._references.contained_resource_path(root, root / f"{normalized_id}.yaml", "specialization"),
                        self._references.contained_resource_path(
                            root,
                            root / f"{normalized_id.removeprefix('specialization.')}.yaml",
                            "specialization",
                        ),
                    ]
                )
        unique: list[Path] = []
        seen: set[Path] = set()
        for path in candidates:
            resolved = path.resolve()
            if resolved not in seen:
                seen.add(resolved)
                unique.append(resolved)
        return unique

    def manifest_index(self, workplace_manifest: Path | None, project_root: Path | None = None) -> dict[str, dict[str, Any]]:
        workplace_root = workplace_manifest.parent if workplace_manifest and workplace_manifest.is_file() else None
        index: dict[str, dict[str, Any]] = {}
        paths: list[Path] = []
        if workplace_root:
            registry = self._inputs.load_yaml_document(self.registry_path(workplace_root))
            entries = registry.get("specializations") if isinstance(registry, dict) else []
            if isinstance(entries, list):
                for entry in entries:
                    if isinstance(entry, dict):
                        path = self.path_from_registry_entry(workplace_root, entry, workplace_manifest)
                        if path:
                            paths.append(path)
            for root in [workplace_root / "specializations", workplace_root / "specializations" / "user", workplace_root / "specializations" / "custom"]:
                if root.is_dir():
                    paths.extend(sorted(root.glob("*.yaml")))
                    paths.extend(sorted(root.glob("*.yml")))
        if project_root:
            flow_root = ProjectMetadataReader(project_root).flow_root()
            for root in [flow_root / "specializations", flow_root / "specializations" / "user", flow_root / "specializations" / "custom"]:
                if root.is_dir():
                    paths.extend(sorted(root.glob("*.yaml")))
                    paths.extend(sorted(root.glob("*.yml")))
        for path in paths:
            data = self._inputs.load_yaml_document(path)
            if not isinstance(data, dict) or yaml_error(data) or not data.get("id"):
                continue
            normalized_id = self.resource_id(str(data["id"]))
            source = "project" if project_root and path_is_relative_to(path, ProjectMetadataReader(project_root).flow_root()) else "workplace"
            record = dict(data)
            record["id"] = normalized_id
            record["__manifest_path"] = path
            record["__source"] = source
            index[normalized_id] = record
        return index

    def manifest_path(self, workplace_root: Path, specialization_id: str) -> Path | None:
        normalized_id = self.resource_id(specialization_id)
        for candidate in self.path_candidates(workplace_root, normalized_id, None):
            if candidate.is_file():
                return candidate
        return None
