"""Existing private resource path registry publication."""
from __future__ import annotations

from pathlib import Path

from processforge_core.project.registry_write import WorkplaceRegistryWriter


class PrivateResourcePathWriter:
    """Publish a private resource path through the existing registry writer."""

    def __init__(self, distribution_root: Path) -> None:
        self.distribution_root = distribution_root
        self.registry = WorkplaceRegistryWriter(distribution_root)

    def ensure(self, workplace_root: Path, resource_id: str, raw_path: str) -> Path:
        target = workplace_root / "registries" / "private-resource-paths.yaml"
        entry = {
            "id": resource_id,
            "label": resource_id.replace("-", " ").title(),
            "path": raw_path,
            "visibility": "private",
            "status": "available",
        }
        self.registry.upsert(target, "private_resource_paths", entry)
        return target
