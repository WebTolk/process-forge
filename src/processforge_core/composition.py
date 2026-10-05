"""Internal, explicit service composition; construction performs no I/O."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from types import ModuleType
from typing import TYPE_CHECKING, Any, Callable

from .garage import CurrentWorkService
from .ports import WorkContextReadPort, WorkReadCorePort, WorkRecordReadPort
from .work_records import YamlWorkRecordReader

if TYPE_CHECKING:
    from .diagnostics import Logger
    from .process_execution import ProcessExecutionService
    from .work_context_read import WorkContextReadService

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


@dataclass(frozen=True)
class LegacyWorkContextAdapter:
    project_root: Path
    core: Any

    def validate_contract(self, path: Path, assignment: dict[str, Any], capsule: dict[str, Any]) -> dict[str, Any]:
        from .work_context import validate_execution_contract

        return validate_execution_contract(self.project_root, path, assignment, capsule, self.core, check_sources=False)

    def normalize_assignment(self, path: Path, assignment: dict[str, Any]) -> dict[str, Any]:
        from .work_context import normalized_assignment_contract

        return normalized_assignment_contract(self.project_root, path, assignment, self.core)


def build_work_context_read_service(
    project_root: Path, core: Any, *, flow_root: Callable[[], Path], assignment_path: Callable[[str], Path],
) -> WorkContextReadService:
    from .work_context_read import WorkContextReadService

    adapter = LegacyWorkContextAdapter(project_root, core)
    return WorkContextReadService(flow_root, assignment_path, adapter.validate_contract, adapter.normalize_assignment)


def build_process_execution_service(
    project_root: Path, workplace_root: Path | None, core: Any, *, observer: Logger | None = None,
    records: WorkRecordReadPort | None = None,
    context: WorkContextReadPort | None = None,
) -> ProcessExecutionService:
    from .process_execution import ProcessExecutionService

    if records is None:
        records = YamlWorkRecordReader(project_root, core)
    return ProcessExecutionService(project_root, workplace_root, core, observer=observer, records=records, context=context)
