"""Internal, explicit composition of the current-work read service."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from types import ModuleType
from typing import Any

from .garage import CurrentWorkService
from .ports import WorkReadCorePort

__all__ = ()


@dataclass(frozen=True)
class LegacyWorkReadAdapter:
    core: ModuleType

    def locate_flow_root(self, project_root: Path) -> Path:
        return self.core.locate_flow_root(project_root)

    def load_yaml_document(self, path: Path) -> dict[str, Any]:
        return self.core.load_yaml_document(path)


def build_current_work_service(project_root: Path, core: WorkReadCorePort) -> CurrentWorkService:
    return CurrentWorkService(project_root, core)
