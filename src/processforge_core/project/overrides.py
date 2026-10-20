"""Existing project override reads and overlay rules through concrete Core owners."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from ..common.digests import FileDigestReader
from ..common.paths import rel
from ..common.values import as_list
from ..common.yaml_io import _parse_simple_yaml, yaml_error
from ..configuration.specializations import SpecializationCatalogReader
from ..documents.reader import YamlDocumentReader
from ..resources.buckets import default_resource_buckets, dedupe_sorted, merge_resource_buckets
from ..work.context_documents import ContextContractInputs

PROJECT_OVERRIDE_MODES = {"overlay", "extension", "replace", "parameterize", "disable", "fork"}

PROJECT_OVERRIDE_KINDS = {
    "template": "templates",
    "templates": "templates",
    "knowledge_package": "knowledge_packages",
    "knowledge_packages": "knowledge_packages",
    "tool": "tools",
    "tools": "tools",
    "mcp": "mcp",
    "specialization": "specializations",
    "specializations": "specializations",
}


class ProjectOverrideReader:
    """Keep operation-local documents and the original override algorithm order."""

    def __init__(self, distribution_root: Path) -> None:
        self._documents = YamlDocumentReader(_parse_simple_yaml)
        self._inputs = ContextContractInputs(documents=self._documents)
        self._specialization_catalog_reader = SpecializationCatalogReader(distribution_root)
        self._file_digests = FileDigestReader()

    def project_overrides_path(self, project_root: Path) -> Path:
        return self._inputs.locate_flow_root(project_root) / "project-overrides.yaml"

    def load_project_overrides(self, project_root: Path) -> dict[str, Any]:
        path = self.project_overrides_path(project_root)
        data = self._documents.load(path)
        if not isinstance(data, dict) or yaml_error(data):
            return {"schema_version": 1, "kind": "processforge.project_overrides", "overrides": {}}
        overrides = data.get("overrides")
        if not isinstance(overrides, dict):
            data["overrides"] = {}
        return data

    def project_override_entries(self, project_root: Path) -> list[dict[str, Any]]:
        data = self.load_project_overrides(project_root)
        overrides = data.get("overrides") if isinstance(data.get("overrides"), dict) else {}
        entries: list[dict[str, Any]] = []
        for raw_kind, items in overrides.items():
            kind = PROJECT_OVERRIDE_KINDS.get(str(raw_kind), str(raw_kind))
            for item in items if isinstance(items, list) else []:
                if isinstance(item, dict) and item.get("target"):
                    record = dict(item)
                    record["kind"] = kind
                    record["source"] = rel(self.project_overrides_path(project_root), project_root)
                    entries.append(record)
        return entries

    def project_specialization_override_entries(self, project_root: Path, specialization_id: str) -> list[dict[str, Any]]:
        target_id = self._specialization_catalog_reader.resource_id(specialization_id)
        return [
            entry
            for entry in self.project_override_entries(project_root)
            if str(entry.get("kind") or "") == "specializations"
            and self._specialization_catalog_reader.resource_id(str(entry.get("target") or "")) == target_id
        ]

    def project_override_path(self, project_root: Path, entry: dict[str, Any]) -> Path | None:
        raw = entry.get("path") or entry.get("project_package")
        if not raw:
            return None
        path = Path(str(raw))
        if path.is_absolute():
            return path
        return project_root / path

    def load_project_override_document(self, project_root: Path, entry: dict[str, Any]) -> dict[str, Any]:
        path = self.project_override_path(project_root, entry)
        if not path or not path.is_file():
            return {}
        data = self._documents.load(path)
        return data if isinstance(data, dict) and not yaml_error(data) else {}

    def apply_specialization_overlay(
        self,
        spec: dict[str, Any],
        overlay: dict[str, Any],
        mode: str,
    ) -> tuple[dict[str, Any], list[str]]:
        effective = dict(spec)
        notes: list[str] = []
        if mode == "replace":
            effective = dict(overlay)
            notes.append("replace document applied")
        else:
            resources = default_resource_buckets()
            merge_resource_buckets(resources, spec.get("resources") if isinstance(spec.get("resources"), dict) else {})
            merge_resource_buckets(resources, overlay.get("resources") if isinstance(overlay.get("resources"), dict) else {})
            effective["resources"] = resources
            capabilities = set(str(item) for item in as_list(spec.get("provides_capabilities")) if str(item))
            capabilities.update(str(item) for item in as_list(overlay.get("provides_capabilities")) if str(item))
            effective["provides_capabilities"] = dedupe_sorted(list(capabilities))
            overlay_bindings = overlay.get("platform_bindings") if isinstance(overlay.get("platform_bindings"), list) else []
            if overlay_bindings:
                effective["platform_bindings"] = list(as_list(spec.get("platform_bindings"))) + [item for item in overlay_bindings if isinstance(item, dict)]
            notes.append(f"{mode} overlay applied")
        for key in ["__source", "__manifest_path"]:
            if key in spec and key not in effective:
                effective[key] = spec[key]
        return effective, notes

    def sha256_optional_file(self, path: Path | None) -> str:
        return "sha256:" + self._file_digests.sha256_file(path) if path and path.is_file() else "missing"

    def effective_fingerprint_for(self, base_id: str, base_path: Path | None, override_path: Path | None, mode: str) -> str:
        stable = {
            "id": base_id,
            "base_sha256": self.sha256_optional_file(base_path),
            "override_sha256": self.sha256_optional_file(override_path),
            "mode": mode,
        }
        return "sha256:" + hashlib.sha256(json.dumps(stable, sort_keys=True).encode("utf-8")).hexdigest()

    def resolved_override_record(self, project_root: Path, entry: dict[str, Any], base_path: Path | None = None) -> dict[str, Any]:
        override_path = self.project_override_path(project_root, entry)
        mode = str(entry.get("mode") or "extension")
        target = str(entry.get("target") or "")
        record = {
            "kind": str(entry.get("kind") or ""),
            "target": target,
            "mode": mode,
            "reason": str(entry.get("reason") or ""),
            "path": rel(override_path, project_root) if override_path else "",
            "sha256": self.sha256_optional_file(override_path),
            "base_sha256": self.sha256_optional_file(base_path),
            "effective_fingerprint": self.effective_fingerprint_for(target, base_path, override_path, mode),
        }
        if isinstance(entry.get("params"), dict):
            record["params"] = entry["params"]
        if entry.get("project_package"):
            record["project_package"] = str(entry["project_package"])
        return record

    def apply_resource_excludes(self, required: set[str], candidates: set[str], excludes: set[str], conflicts: list[dict[str, Any]], source: str, kind: str) -> set[str]:
        for item in sorted(required.intersection(excludes)):
            conflicts.append({"id": item, "kind": kind, "source": source, "reason": "cannot exclude required resource"})
        return candidates - (excludes - required)
