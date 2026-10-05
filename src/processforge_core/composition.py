"""Internal, explicit service composition; construction performs no I/O."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from types import ModuleType
from typing import TYPE_CHECKING, Any

from .garage import CurrentWorkService
from .ports import WorkReadCorePort, WorkRecordReadPort
from .work_records import YamlWorkRecordReader

if TYPE_CHECKING:
    from .diagnostics import Logger
    from .process_execution import ProcessExecutionService

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


def build_process_execution_service(
    project_root: Path, workplace_root: Path | None, core: Any, *, observer: Logger | None = None,
    records: WorkRecordReadPort | None = None,
) -> ProcessExecutionService:
    from .process_execution import ProcessExecutionService

    if records is None:
        records = YamlWorkRecordReader(project_root, core)
    return ProcessExecutionService(project_root, workplace_root, core, observer=observer, records=records)
