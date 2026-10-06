"""Existing project snapshot reads with explicit, uncached dependencies."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

__all__ = ()


@dataclass(frozen=True)
class ProjectSnapshotReadService:
    snapshot_path: Callable[[], Path]
    load_document: Callable[[Path], dict[str, Any]]
    sha256_file: Callable[[Path], str]

    def load(self, path: Path | None = None) -> dict[str, Any]:
        return self.load_document(self.snapshot_path() if path is None else path)

    def checksum(self, path: Path) -> str:
        return "sha256:" + self.sha256_file(path) if path.is_file() else ""
