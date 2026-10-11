"""Concrete live project snapshot reads, separate from lifecycle authority."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ..common.digests import FileDigestReader
from ..common.yaml_io import _parse_simple_yaml
from ..documents.reader import YamlDocumentReader
from ..ports import ProjectSnapshotReadPort
from ..work.context_documents import ContextContractInputs

__all__ = ()


@dataclass(frozen=True)
class ProjectSnapshotReadService:
    project_root: Path
    documents: YamlDocumentReader = field(
        default_factory=lambda: YamlDocumentReader(_parse_simple_yaml),
        kw_only=True, repr=False, compare=False,
    )
    digests: FileDigestReader = field(
        default_factory=FileDigestReader, kw_only=True, repr=False, compare=False,
    )

    def snapshot_path(self) -> Path:
        path, _markdown = ContextContractInputs().project_context_snapshot_paths(self.project_root)
        return path

    def load(self, path: Path | None = None) -> dict[str, Any]:
        return self.documents.load(self.snapshot_path() if path is None else path)

    def checksum(self, path: Path) -> str:
        return "sha256:" + self.digests.sha256_file(path) if path.is_file() else ""


def load_snapshot(
    project_root: Path, *, snapshots: ProjectSnapshotReadPort | None = None,
) -> dict[str, Any]:
    if snapshots is None:
        from ..composition import build_project_context_snapshot_read_service

        snapshots = build_project_context_snapshot_read_service(project_root)
    return snapshots.load()
