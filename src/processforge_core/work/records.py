"""Internal live Run/Assignment reader; callers supply validated identifiers."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterator

from ..ports import WorkReadCorePort
from .inventory import WorkInventory

__all__ = ()


@dataclass(frozen=True)
class YamlWorkRecordReader:
    project_root: Path
    core: WorkReadCorePort

    def runs(self) -> Iterator[tuple[Path, dict[str, Any]]]:
        inventory = WorkInventory(self.core.locate_flow_root(self.project_root), self.core.load_yaml_document)
        yield from inventory.runs()

    def load_run(self, run_id: str) -> dict[str, Any]:
        path = self.core.locate_flow_root(self.project_root) / "runs" / run_id / "run.yaml"
        return self.core.load_yaml_document(path)

    def load_assignment(self, assignment_id: str) -> dict[str, Any]:
        inventory = WorkInventory(self.core.locate_flow_root(self.project_root), self.core.load_yaml_document)
        return inventory.assignment(assignment_id)
