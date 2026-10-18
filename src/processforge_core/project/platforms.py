"""Live platform contract discovery and document reads."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from ..common.yaml_io import yaml_error
from ..resources.snapshot import WorkspacePathReferenceReader
from ..work.context_documents import ContextContractInputs
from .metadata import PROJECT_FLOW_ROOT


class PlatformContractReader:
    """Read the existing seed, project and workplace platform overlays."""

    def __init__(self, distribution_root: Path):
        self.distribution_root = distribution_root
        self._inputs = ContextContractInputs()

    def contract_id(self, platform_id: str) -> str:
        return platform_id if platform_id.startswith("platform.") or platform_id.startswith("fixture.platform.") else f"platform.{platform_id}"

    def registry_entry(self, workplace_manifest: Path | None, contract_id: str) -> dict[str, Any] | None:
        references = WorkspacePathReferenceReader(
            self.distribution_root,
            workplace_manifest.parent if workplace_manifest else None,
            workplace_manifest=workplace_manifest,
            inputs=self._inputs,
        )
        registry = references.load_workplace_registry(workplace_manifest, "platforms", "platforms.yaml")
        entries = registry.get("platforms") if isinstance(registry, dict) else None
        if not isinstance(entries, list):
            return None
        aliases = {contract_id, contract_id.removeprefix("platform.")}
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            entry_ids = {str(entry.get("id", "")), str(entry.get("package_id", ""))}
            if aliases.intersection(entry_ids):
                return entry
        return None

    def seed_paths(self, distribution_root: Path | None = None) -> list[Path]:
        root = distribution_root or self.distribution_root
        seed_root = root / "seeds" / "platform-contracts"
        if not seed_root.is_dir():
            return []
        return sorted([*seed_root.glob("*.yaml"), *seed_root.glob("*.yml")])

    def project_paths(self, project_root: Path | None) -> list[Path]:
        if not project_root:
            return []
        candidates: list[Path] = []
        for root in [project_root / PROJECT_FLOW_ROOT / "platform-contracts", project_root / "platform-contracts"]:
            if root.is_dir():
                candidates.extend(sorted(root.glob("*.yaml")))
                candidates.extend(sorted(root.glob("*.yml")))
                candidates.extend(sorted(root.glob("*/platform-contract.yaml")))
                candidates.extend(sorted(root.glob("*/platform-contract.yml")))
        return candidates

    def record(self, path: Path, source: str, registry_entry: dict[str, Any] | None = None) -> tuple[str, dict[str, Any]] | None:
        data = self._inputs.load_yaml_document(path)
        if not data or yaml_error(data):
            return None
        contract_id = data.get("id")
        if not contract_id:
            return None
        normalized_id = self.contract_id(str(contract_id))
        return normalized_id, {"contract": data, "path": path, "source": source, "status": "available", "registry_entry": registry_entry}

    def index(self, workplace_manifest: Path | None, project_root: Path | None = None) -> dict[str, dict[str, Any]]:
        index: dict[str, dict[str, Any]] = {}
        for path in self.seed_paths(self.distribution_root):
            record = self.record(path, "seed")
            if record:
                index[record[0]] = record[1]
        for path in self.project_paths(project_root):
            record = self.record(path, "project")
            if record:
                index[record[0]] = record[1]
        references = WorkspacePathReferenceReader(
            project_root or self.distribution_root,
            workplace_manifest.parent if workplace_manifest else None,
            workplace_manifest=workplace_manifest,
            inputs=self._inputs,
        )
        registry = references.load_workplace_registry(workplace_manifest, "platforms", "platforms.yaml")
        entries = registry.get("platforms") if isinstance(registry, dict) else None
        if isinstance(entries, list) and workplace_manifest:
            for entry in entries:
                if not isinstance(entry, dict) or str(entry.get("status", "available")) in {"missing", "disabled"}:
                    continue
                raw_path = entry.get("path")
                if not raw_path:
                    continue
                path = references.resolve_registry_relative_path(workplace_manifest.parent, str(raw_path), workplace_manifest)
                record = self.record(path, "workplace", entry)
                if record:
                    index[record[0]] = record[1]
        return index

    def load(self, workplace_manifest: Path | None, contract_id: str, project_root: Path | None = None) -> tuple[dict[str, Any], dict[str, Any] | None, str, str]:
        normalized_id = self.contract_id(contract_id)
        entry = self.index(workplace_manifest, project_root).get(normalized_id)
        if entry:
            return entry["contract"], entry.get("registry_entry"), str(entry.get("status", "available")), str(entry.get("source", "manifest"))
        registry_entry = self.registry_entry(workplace_manifest, normalized_id)
        if registry_entry and str(registry_entry.get("status", "available")) in {"missing", "disabled"}:
            return {"id": normalized_id, "requires": {}, "includes": {}}, registry_entry, str(registry_entry.get("status")), "registry"
        return {"id": normalized_id, "requires": {}, "includes": {}}, registry_entry, "missing", "missing"
