"""Resource record normalization with the existing live path and snapshot owners."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ..common.ids import safe_id
from ..project.resource_snapshot import ResourceSnapshotRules
from ..work.context_documents import ContextContractInputs, PATH_CONSTANT_PATTERN
from .snapshot import WorkspacePathReferenceReader


HEAVY_RESOURCE_KINDS = {
    "source_tree",
    "documentation",
    "article_collection",
    "note_collection",
    "snippet_collection",
    "example_collection",
    "dataset",
    "media_reference",
}


class ResourceRecordService:
    def load_policy(self, kind: str, requested: str | None = None) -> str:
        if requested:
            return requested
        return "on_demand" if kind in HEAVY_RESOURCE_KINDS else "when_relevant"

    def index_policy(self, kind: str, requested: str | None = None) -> str:
        if requested:
            return requested
        if kind in {"source_tree"}:
            return "symbols"
        if kind in {"documentation", "article", "article_collection"}:
            return "full_text"
        return "metadata"

    def known_root(self, workplace_root: Path, raw_path: str) -> dict[str, Any] | None:
        inputs = ContextContractInputs()
        paths = WorkspacePathReferenceReader(workplace_root, workplace_root, inputs=inputs)
        resource_resolution = paths.workplace_path_resolution(workplace_root, raw_path)
        if resource_resolution.get("errors"):
            return None
        resource_resolved = paths.normalize_path_string(str(resource_resolution.get("resolved", ""))).rstrip("/")
        registry_specs = [
            ("knowledge_roots", "knowledge-roots.yaml", "knowledge_roots"),
            ("template_roots", "templates.yaml", "template_roots"),
            ("package_roots", "package-roots.yaml", "package_roots"),
        ]
        for registry_name, registry_file, collection_key in registry_specs:
            registry = inputs.load_yaml_document(workplace_root / "registries" / registry_file)
            entries = registry.get(collection_key) if isinstance(registry, dict) else None
            if not isinstance(entries, list):
                continue
            for entry in entries:
                if not isinstance(entry, dict) or not entry.get("id") or not entry.get("path"):
                    continue
                root_resolution = paths.workplace_path_resolution(workplace_root, str(entry["path"]))
                if root_resolution.get("errors"):
                    continue
                root_resolved = paths.normalize_path_string(str(root_resolution.get("resolved", ""))).rstrip("/")
                if resource_resolved == root_resolved or resource_resolved.startswith(root_resolved + "/"):
                    path_ref: dict[str, Any] = {"registry": registry_name, "id": str(entry["id"])}
                    if resource_resolved != root_resolved:
                        path_ref["relative_path"] = resource_resolved[len(root_resolved) + 1 :]
                    return path_ref
        return None

    def public_ref(self, resource_id: str, raw_path: str | None, source_url: str | None = None, workplace_root: Path | None = None) -> dict[str, Any]:
        if source_url:
            return {"registry": "external_resources", "id": resource_id, "url": source_url}
        if raw_path:
            if workplace_root:
                known_ref = self.known_root(workplace_root, raw_path)
                if known_ref:
                    return known_ref
            if ContextContractInputs().path_string_is_absolute(raw_path) or PATH_CONSTANT_PATTERN.search(raw_path):
                return {"registry": "private_resource_paths", "id": resource_id}
            return {"package": "self", "relative_path": raw_path}
        return {"registry": "external_resources", "id": resource_id}

    def normalize(self, resource: dict[str, Any], package_id: str, workplace_root: Path | None = None, *, register_private_path: bool = False) -> dict[str, Any]:
        record = dict(resource)
        resource_id = safe_id(str(record.get("id") or record.get("title") or "resource"), "resource")
        kind = str(record.get("kind") or "reference")
        raw_path = str(record.get("path")) if record.get("path") else None
        source = record.get("source") if isinstance(record.get("source"), dict) else {}
        source_url = str(source.get("url") or record.get("url") or "") or None
        record["id"] = resource_id
        record["kind"] = kind
        record["title"] = str(record.get("title") or resource_id.replace("-", " ").title())
        record["load_policy"] = self.load_policy(kind, str(record.get("load_policy")) if record.get("load_policy") else None)
        record["index_policy"] = self.index_policy(kind, str(record.get("index_policy")) if record.get("index_policy") else None)
        if "path_ref" not in record:
            record["path_ref"] = self.public_ref(resource_id, raw_path, source_url, workplace_root)
        if raw_path and (ContextContractInputs().path_string_is_absolute(raw_path) or PATH_CONSTANT_PATTERN.search(raw_path)):
            record["path_status"] = "resolved_private_path_hidden"
            resolution = WorkspacePathReferenceReader(workplace_root, workplace_root).workplace_path_resolution(workplace_root, raw_path) if workplace_root else None
            if resolution and resolution.get("errors"):
                record["path_resolution"] = {"status": "error", "errors": resolution.get("errors")}
            elif record.get("path_ref", {}).get("registry") == "private_resource_paths":
                record["registration_hint"] = "register a knowledge_root/template_root/package_root if this path should be shared by multiple resources"
        record.pop("path", None)
        if source_url and "source" not in record:
            record["source"] = {"type": "url", "url": source_url}
        if "update_policy" not in record:
            record["update_policy"] = {"mode": "manual"}
        versioning, retention, snapshot_behavior = ResourceSnapshotRules().versioning_policy(record)
        record.setdefault("versioning", versioning)
        record.setdefault("retention", retention)
        record.setdefault("snapshot_behavior", snapshot_behavior)
        if "package" not in record:
            record["package"] = package_id
        return record
