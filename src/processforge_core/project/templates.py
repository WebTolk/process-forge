"""Resolve workplace template roots and discover their existing manifests."""

from __future__ import annotations

from pathlib import Path

from ..resources.snapshot import WorkspacePathReferenceReader
from ..work.context_documents import ContextContractInputs
from .registry_write import WorkplaceRegistryWriter


class TemplateCatalogService:
    """Coordinate concrete readers and the existing workplace registry writer."""

    def __init__(self, distribution_root: Path) -> None:
        self.distribution_root = distribution_root
        self._inputs = ContextContractInputs()
        self._registry_writer = WorkplaceRegistryWriter(distribution_root)

    def resolve_root(self, workplace_root: Path, template_root_id: str | None = None, *, mode: str = "read") -> tuple[str, Path]:
        registry_path = workplace_root / "registries" / "templates.yaml"
        data = self._inputs.load_yaml_document(registry_path)
        roots = data.get("template_roots") if isinstance(data, dict) else None
        entries = [entry for entry in roots if isinstance(entry, dict)] if isinstance(roots, list) else []
        if not entries:
            entries = [{"id": "global", "label": "Global reusable templates", "path": "${PF_TEMPLATES}", "scope": "workplace", "status": "available"}]
            if mode == "write":
                self._registry_writer.upsert(registry_path, "template_roots", entries[0])
        selected = None
        if template_root_id:
            for entry in entries:
                if str(entry.get("id")) == template_root_id:
                    selected = entry
                    break
            if selected is None:
                raise SystemExit(f"FAIL: template root '{template_root_id}' not found in registries/templates.yaml")
        else:
            available = [entry for entry in entries if str(entry.get("status", "available")) == "available"]
            selected = available[0] if available else entries[0]
        root_id = str(selected.get("id", "global"))
        references = WorkspacePathReferenceReader(
            workplace_root, workplace_root,
            workplace_manifest=workplace_root / "workplace.yaml",
            inputs=self._inputs,
        )
        root_path = references.path_resolution_to_path(references.workplace_path_resolution(workplace_root, str(selected.get("path") or "${PF_TEMPLATES}")))
        if mode == "write":
            root_path.mkdir(parents=True, exist_ok=True)
        return root_id, root_path

    def manifest(self, workplace_root: Path, template_id: str) -> Path | None:
        _root_id, root_path = self.resolve_root(workplace_root, None, mode="read")
        candidate = root_path / template_id / "template.yaml"
        if candidate.is_file():
            return candidate
        registry = self._inputs.load_yaml_document(workplace_root / "registries" / "templates.yaml")
        entries = registry.get("templates") if isinstance(registry, dict) else None
        if isinstance(entries, list):
            for entry in entries:
                if isinstance(entry, dict) and str(entry.get("id")) == template_id and entry.get("path"):
                    path = workplace_root / str(entry["path"])
                    return path if path.is_file() else None
        return None
