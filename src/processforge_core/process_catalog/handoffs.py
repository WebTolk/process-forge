"""Read handoff documents and construct their existing project paths."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ..common.ids import safe_id
from ..common.yaml_io import _parse_simple_yaml
from ..documents.reader import YamlDocumentReader
from ..project.metadata import ProjectMetadataReader


class HandoffDocumentReader:
    """Locate and softly read current handoff documents without lifecycle effects."""

    def __init__(self) -> None:
        self.documents = YamlDocumentReader(_parse_simple_yaml)

    def directory(self, project_root: Path, handoff_id: str) -> Path:
        return ProjectMetadataReader(project_root, documents=self.documents).flow_root() / "handoffs" / safe_id(handoff_id, "handoff")

    def path(self, project_root: Path, handoff_id: str) -> Path:
        return self.directory(project_root, handoff_id) / "handoff.yaml"

    def read(self, project_root: Path, handoff_id: str) -> dict[str, Any]:
        data = self.documents.load(self.path(project_root, handoff_id))
        if not data:
            raise SystemExit(f"FAIL: handoff not found: {safe_id(handoff_id, 'handoff')}")
        return data
