"""Live project metadata reads through concrete Core document infrastructure."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ..common.ids import safe_id
from ..common.yaml_io import _parse_simple_yaml
from ..documents.reader import YamlDocumentReader

PROJECT_FLOW_ROOT = ".pf"


@dataclass(frozen=True)
class ProjectMetadataReader:
    project_root: Path
    documents: YamlDocumentReader = field(
        default_factory=lambda: YamlDocumentReader(_parse_simple_yaml),
    )

    def flow_root(self, *, prefer_pf: bool = True) -> Path:
        return self.project_root / PROJECT_FLOW_ROOT

    def manifest(self) -> dict[str, Any]:
        return self.documents.load(self.flow_root() / "process-forge.yaml")

    def project_id(self) -> str:
        data = self.manifest()
        project = data.get("project") if isinstance(data, dict) else None
        if isinstance(project, dict) and project.get("id"):
            return str(project["id"])
        return safe_id(self.project_root.name, "project")
