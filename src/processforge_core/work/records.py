"""Internal live Run/Assignment reader; callers supply validated identifiers."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterator

from ..common.yaml_io import _parse_simple_yaml
from ..documents.reader import YamlDocumentReader
from .projection import WorkProjectionPolicy
from .inventory import WorkInventory

__all__ = ()


@dataclass(frozen=True)
class YamlWorkRecordReader:
    project_root: Path
    documents: YamlDocumentReader = field(default_factory=lambda: YamlDocumentReader(_parse_simple_yaml))

    @property
    def flow_root(self) -> Path:
        return self.project_root / ".pf"

    def assignment_path(self, assignment_id: str) -> Path:
        return self.flow_root / "assignments" / f"{assignment_id}.yaml"

    def runs(self) -> Iterator[tuple[Path, dict[str, Any]]]:
        inventory = WorkInventory(self.flow_root, self.documents.load)
        yield from inventory.runs()

    def load_run(self, run_id: str) -> dict[str, Any]:
        path = self.flow_root / "runs" / run_id / "run.yaml"
        return self.documents.load(path)

    def load_assignment(self, assignment_id: str) -> dict[str, Any]:
        inventory = WorkInventory(self.flow_root, self.documents.load)
        return inventory.assignment(assignment_id)


@dataclass(frozen=True)
class CurrentWorkService:
    project_root: Path
    documents: YamlDocumentReader = field(default_factory=lambda: YamlDocumentReader(_parse_simple_yaml))

    def summary(self) -> dict[str, Any]:
        active = self.active_items()
        projection = WorkProjectionPolicy()
        return {
            "governed": bool(active),
            "active_runs": projection.compact_active_runs(active),
            "active_work": active[:10],
            "recommendation": "continue" if active else "start_work",
        }

    def active_items(self) -> list[dict[str, Any]]:
        return [item for item in self.items() if item["state"] == "active" and not item["bootstrap_placeholder"]]

    def find_by_objective(self, objective: str) -> dict[str, Any]:
        projection = WorkProjectionPolicy()
        normalized = projection.normalize_objective(objective)
        active: list[dict[str, Any]] = []
        historical: list[dict[str, Any]] = []
        for item in self.items():
            if item["bootstrap_placeholder"] or projection.normalize_objective(str(item.get("objective") or "")) != normalized:
                continue
            if item["state"] == "active":
                active.append(item)
            elif item["state"] == "historical":
                historical.append(item)
        return {"active": active[0] if active else None, "historical": historical}

    def items(self) -> list[dict[str, Any]]:
        records = YamlWorkRecordReader(self.project_root, self.documents)
        projection = WorkProjectionPolicy()
        rows: list[dict[str, Any]] = []
        for run_path, run in records.runs():
            run_status = str(run.get("status") or "")
            run_id = str(run.get("id") or run_path.parent.name)
            tasks = run.get("tasks") if isinstance(run.get("tasks"), list) else []
            if not tasks:
                rows.append(projection.work_item(run_id=run_id, run_status=run_status, task={}, run=run))
            for entry in tasks:
                if not isinstance(entry, dict):
                    continue
                task_id = str(entry.get("id") or "")
                task_path = records.assignment_path(task_id)
                task = records.load_assignment(task_id) if task_path.is_file() else {"id": task_id, "status": entry.get("status"), "objective": run.get("objective")}
                rows.append(projection.work_item(run_id=run_id, run_status=run_status, task=task, run=run))
        first = records.assignment_path("first-assignment")
        if first.is_file():
            task = records.load_assignment("first-assignment")
            rows.append(projection.work_item(run_id="", run_status="", task=task, run={}))
        return rows
