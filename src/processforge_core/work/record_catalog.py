"""Existing validated Work record catalog with explicit live dependencies."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable, Collection, Iterator, Pattern, Protocol

if TYPE_CHECKING:
    from ..ports import WorkRecordReadPort


class WorkCatalogInventory(Protocol):
    def runs(self) -> Iterator[tuple[Path, dict[str, Any]]]: ...
    def assignment(self, assignment_id: str) -> dict[str, Any]: ...


class WorkCatalogInventoryFactory(Protocol):
    def __call__(self, flow_root: Path, load_document: Callable[[Path], dict[str, Any]]) -> WorkCatalogInventory: ...


class CompletionIntentLookup(Protocol):
    def __call__(self, run: dict[str, Any], assignment: dict[str, Any]) -> tuple[dict[str, Any] | None, object]: ...


@dataclass(frozen=True, kw_only=True)
class WorkRecordCatalogService:
    record_reader: Callable[[], WorkRecordReadPort | None] = field(repr=False, compare=False)
    inventory_factory: Callable[[], WorkCatalogInventoryFactory] = field(repr=False, compare=False)
    flow_root: Callable[[], Callable[[], Path]] = field(repr=False, compare=False)
    document_loader: Callable[[], Callable[[Path], dict[str, Any]]] = field(repr=False, compare=False)
    identifier_pattern: Callable[[], Pattern[str]] = field(repr=False, compare=False)
    intent_reader: Callable[[], CompletionIntentLookup] = field(repr=False, compare=False)
    active_assignment_statuses: Callable[[], Collection[str]] = field(repr=False, compare=False)
    active_run_statuses: Callable[[], Collection[str]] = field(repr=False, compare=False)

    def records(self, *, include_historical: bool) -> list[dict[str, Any]]:
        records: list[dict[str, Any]] = []
        if self.record_reader() is None:
            inventory = self.inventory_factory()(self.flow_root()(), self.document_loader())
            run_documents, load_assignment = inventory.runs(), inventory.assignment
        else:
            run_documents, load_assignment = self.record_reader().runs(), self.record_reader().load_assignment
        for path, run in run_documents:
            run_id = str(run.get("id") or path.parent.name)
            if not self.identifier_pattern().fullmatch(run_id):
                continue
            for entry in run.get("tasks", []) if isinstance(run.get("tasks"), list) else []:
                if not isinstance(entry, dict) or not entry.get("id"):
                    continue
                entry_id = str(entry["id"])
                if not self.identifier_pattern().fullmatch(entry_id):
                    continue
                task = load_assignment(entry_id)
                if not task:
                    continue
                task_id = str(task.get("id") or entry_id)
                if not self.identifier_pattern().fullmatch(task_id) or str(task.get("run_id") or run_id) != run_id:
                    continue
                status = str(task.get("status") or entry.get("status") or "")
                pending_completion, _intent_error = self.intent_reader()(run, task)
                has_pending_completion = pending_completion is not None
                active = has_pending_completion or (status in self.active_assignment_statuses() and str(run.get("status") or "") in self.active_run_statuses())
                if not active and not include_historical:
                    continue
                session = task.get("session") if isinstance(task.get("session"), dict) else {}
                records.append(
                    {
                        "run_id": run_id,
                        "assignment_id": task_id,
                        "objective": str(task.get("objective") or run.get("objective") or ""),
                        "status": status,
                        "run_status": str(run.get("status") or ""),
                        "stage": str(task.get("stage") or ""),
                        "active": active,
                        "session_id": str(session.get("id") or ""),
                        "created_at": str(task.get("created_at") or run.get("created_at") or ""),
                        "updated_at": str(task.get("updated_at") or run.get("updated_at") or ""),
                        "pending_completion": has_pending_completion,
                    }
                )
        return records
