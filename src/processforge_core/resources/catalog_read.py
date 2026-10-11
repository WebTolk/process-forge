"""Concrete, live source catalogue for the physical Workplace search index."""
from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import json
from pathlib import Path
from typing import Any

from ..common import yaml_error
from ..common.yaml_io import _parse_simple_yaml
from ..documents.reader import YamlDocumentReader
from ..process_catalog.service import official_pack_manifest_records
from ..work.context_documents import ContextContractInputs
from .snapshot import WorkspacePathReferenceReader, snapshot_with_resolved_search_roots

__all__ = ()


def resource_record_from_package(
    package_id: str, resource: dict[str, Any], requirement: str,
    package_root_id: str | None = None,
) -> dict[str, Any]:
    """Retain the existing package-resource projection and private path refs."""
    resource_id = str(resource.get("id", "resource"))
    record: dict[str, Any] = {
        "id": f"{package_id}:{resource_id}",
        "resource_id": resource_id,
        "package": package_id,
        "requirement": requirement,
        "kind": str(resource.get("kind", "reference")),
        "title": str(resource.get("title", resource_id)),
        "load_policy": str(resource.get("load_policy", "on_demand")),
        "index_policy": str(resource.get("index_policy", "metadata")),
        "status": "indexed",
    }
    if "path_ref" in resource:
        record["path_ref"] = resource["path_ref"]
    elif "path" in resource:
        raw_path = str(resource.get("path", ""))
        if raw_path and Path(raw_path).is_absolute():
            record["path_ref"] = {"registry": "private_resource_paths", "id": resource_id}
            record["path_status"] = "private_absolute_path_redacted"
        elif raw_path:
            if package_root_id:
                record["path_ref"] = {"registry": "package_roots", "id": package_root_id, "relative_path": f"{package_id}/{raw_path}"}
            else:
                record["path_ref"] = {"package": package_id, "relative_path": raw_path}
    for key in ["version", "description", "versioning", "retention", "snapshot_behavior", "generation", "fingerprint", "instance_id", "current_marker_path_ref", "indexing", "selection"]:
        if key in resource:
            record[key] = resource[key]
    return record


@dataclass(frozen=True)
class WorkplaceSearchCatalogReader:
    """Read registered packages, active official knowledge and templates.

    Construction performs no reads. Each operation reads current documents;
    project context, Runtime, Ledger and CLI objects are not dependencies.
    """
    workplace_root: Path
    distribution_root: Path = field(default_factory=lambda: Path(__file__).parents[3], kw_only=True)
    documents: YamlDocumentReader = field(
        default_factory=lambda: YamlDocumentReader(fallback=_parse_simple_yaml),
        kw_only=True, repr=False, compare=False,
    )

    def package_manifest_index(self) -> dict[str, dict[str, Any]]:
        workplace_manifest = self.workplace_root / "workplace.yaml"
        paths = WorkspacePathReferenceReader(
            self.workplace_root, self.workplace_root, workplace_manifest=workplace_manifest,
            inputs=ContextContractInputs(documents=self.documents),
        )
        roots = [
            paths.package_root_resolution_from_entry(self.workplace_root, entry)
            for entry in paths.package_root_entries(self.workplace_root)
        ] if workplace_manifest.is_file() else []
        if not roots:
            roots = [paths.resolve_package_root(self.workplace_root, None, mode="read")]
        candidates: list[Path] = []
        for root in roots:
            if root.warnings or not root.resolved_path.is_dir():
                continue
            candidates.extend(sorted(root.resolved_path.glob("*.yaml")))
            candidates.extend(sorted(root.resolved_path.glob("*.yml")))
            candidates.extend(sorted(root.resolved_path.glob("*/package.yaml")))
            candidates.extend(sorted(root.resolved_path.glob("*/package.yml")))
        registry = paths.load_workplace_registry(workplace_manifest, "process_packs", "process-packs.yaml")
        entries = registry.get("process_packs") if isinstance(registry, dict) else None
        active_ids = {
            str(entry["id"]) for entry in entries if isinstance(entry, dict)
            and entry.get("id") and str(entry.get("status") or "active") in {"active", "enabled", "configured"}
        } if isinstance(entries, list) else set()
        for process_pack_path, process_pack in official_pack_manifest_records(self.distribution_root, documents=self.documents):
            if str(process_pack.get("id") or "") not in active_ids:
                continue
            provided = process_pack.get("provides") if isinstance(process_pack.get("provides"), dict) else {}
            package_ids = provided.get("knowledge_packages")
            for package_id in package_ids if isinstance(package_ids, list) else []:
                package_path = process_pack_path.parent / "knowledge-packages" / f"{package_id}.yaml"
                if package_path.is_file():
                    candidates.append(package_path)
        index: dict[str, dict[str, Any]] = {}
        for path in candidates:
            data = self.documents.load(path)
            if not isinstance(data, dict) or yaml_error(data) or not data.get("id"):
                continue
            package_id = str(data["id"])
            if package_id in index:
                continue
            record = dict(data)
            record["__manifest_path"] = path
            for root in roots:
                try:
                    path.relative_to(root.resolved_path)
                    record["__package_root_id"] = root.root_id
                    break
                except ValueError:
                    continue
            index[package_id] = record
        return index

    def runtime_snapshot(self) -> dict[str, Any]:
        manifest = self.workplace_root / "workplace.yaml"
        package_index = self.package_manifest_index()
        resources: list[dict[str, Any]] = []
        for package_id in sorted(package_index):
            package = package_index[package_id]
            for resource in package.get("resources", []) if isinstance(package.get("resources"), list) else []:
                if isinstance(resource, dict):
                    resources.append(resource_record_from_package(package_id, resource, "registered", package.get("__package_root_id")))
        paths = WorkspacePathReferenceReader(
            self.workplace_root, self.workplace_root, workplace_manifest=manifest,
            inputs=ContextContractInputs(documents=self.documents),
        )
        templates = paths.load_workplace_registry(manifest, "templates", "templates.yaml") if manifest.is_file() else {}
        for entry in templates.get("templates", []) if isinstance(templates, dict) else []:
            if not isinstance(entry, dict) or not entry.get("id") or str(entry.get("status") or "available") in {"missing", "disabled"}:
                continue
            template_id = str(entry["id"])
            resources.append({
                "id": template_id,
                "resource_id": template_id,
                "package_id": str(entry.get("template_root") or ""),
                "kind": "template",
                "title": str(entry.get("title") or template_id),
                "description": str(entry.get("description") or ""),
                "version": str(entry.get("version") or ""),
                "path_ref": {"registry": "templates", "id": template_id},
                "status": str(entry.get("status") or "available"),
                "indexing": entry.get("indexing") if isinstance(entry.get("indexing"), dict) else {
                    "enabled": True, "mode": "metadata", "fields": ["title", "description", "version", "path"],
                    "sources": [
                        {"path": "README.md", "mode": "fulltext", "include": ["README.md"], "role": "description"},
                        {"path": ".", "mode": "metadata", "role": "template_root"},
                    ],
                },
            })
        fingerprint = hashlib.sha256(json.dumps(resources, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()
        snapshot = {
            "search_index_scope": "workplace",
            "snapshot": {"id": "workplace-resource-catalogue", "checksum": f"sha256:{fingerprint}"},
            "local_search_resources": resources,
        }
        return snapshot_with_resolved_search_roots(self.workplace_root, snapshot, self.workplace_root)
