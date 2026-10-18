"""Concrete inputs to project resource resolution, without transport callbacks."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from ..ports import ProjectSnapshotReadPort
from ..project.metadata import ProjectMetadataReader
from ..project.snapshot import ProjectSnapshotReadService
from .snapshot import resolve_garage_path_ref

__all__ = ()


@dataclass(frozen=True)
class ResourceResolveReadService:
    project_root: Path
    workplace_root: Path

    def project_id(self) -> str:
        return ProjectMetadataReader(self.project_root).project_id()

    def read_snapshot(self, snapshots: ProjectSnapshotReadPort | None) -> dict[str, Any]:
        if snapshots is None:
            snapshots = ProjectSnapshotReadService(self.project_root)
        return snapshots.load()

    def path_ref_resolver(self) -> Callable[[dict[str, Any]], dict[str, Any]]:
        return lambda reference: resolve_garage_path_ref(self.project_root, reference, self.workplace_root)
