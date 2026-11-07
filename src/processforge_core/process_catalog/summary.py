"""Live allowed-process summary through the concrete Core catalog reader."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol

from ..process_execution import project_process_selection
from .catalog_read import ProcessCatalogReadService
from .models import ProcessDefinitionRef


class ProcessSummaryCatalogReadPort(Protocol):
    """The definition lookup needed by the summary projection."""

    def resolve_definition(self, process_id: str, /) -> ProcessDefinitionRef: ...


@dataclass(frozen=True, kw_only=True)
class ProcessSummaryReadService:
    project_root: Path | None = None
    catalog: ProcessSummaryCatalogReadPort | None = field(
        default=None,
        repr=False,
        compare=False,
    )

    def summary(
        self, snapshot: dict[str, Any], manifest: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        processes_value = snapshot.get("processes")
        processes = processes_value if isinstance(processes_value, dict) else {}
        current_value = processes.get("current")
        current = current_value if isinstance(current_value, dict) else {}
        selection_value = processes.get("selection")
        selection = (
            selection_value
            if isinstance(selection_value, dict)
            else project_process_selection(manifest or {})
        )
        allowed_value = selection.get("allowed")
        allowed = allowed_value if isinstance(allowed_value, list) else []
        candidates = []
        for process_id in allowed:
            item = {"id": str(process_id), "title": str(process_id), "purpose": ""}
            if self.project_root is not None:
                try:
                    catalog = (
                        self.catalog
                        if self.catalog is not None
                        else ProcessCatalogReadService(self.project_root)
                    )
                    process = catalog.resolve_definition(str(process_id)).process
                    item["title"] = str(process.get("name") or process_id)
                    item["purpose"] = str(
                        process.get("purpose") or process.get("description") or ""
                    )
                except (OSError, ValueError, SystemExit):
                    pass
            candidates.append(item)
        return {
            "id": str(current.get("id") or ""),
            "stage_count": len(current.get("stages") or [])
            if isinstance(current.get("stages"), list)
            else 0,
            "default": str(selection.get("default") or ""),
            "allowed": candidates,
        }
