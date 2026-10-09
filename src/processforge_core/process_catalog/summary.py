"""Existing allowed-process summary through an optional catalog resolver."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ..process_execution import project_process_selection
from .models import ProcessDefinitionRef


@dataclass(frozen=True, kw_only=True)
class ProcessSummaryReadService:
    project_root: Path | None = None
    definition_resolver: Callable[[], Callable[[Path, str], ProcessDefinitionRef]] | None = field(
        default=None, repr=False, compare=False,
    )

    def summary(self, snapshot: dict[str, Any], manifest: dict[str, Any] | None = None) -> dict[str, Any]:
        processes = snapshot.get("processes") if isinstance(snapshot.get("processes"), dict) else {}
        current = processes.get("current") if isinstance(processes.get("current"), dict) else {}
        selection = processes.get("selection") if isinstance(processes.get("selection"), dict) else project_process_selection(manifest or {})
        allowed = selection.get("allowed") if isinstance(selection.get("allowed"), list) else []
        candidates = []
        for process_id in allowed:
            item = {"id": str(process_id), "title": str(process_id), "purpose": ""}
            if self.project_root is not None and self.definition_resolver is not None:
                try:
                    process = self.definition_resolver()(self.project_root, str(process_id)).process
                    item["title"] = str(process.get("name") or process_id)
                    item["purpose"] = str(process.get("purpose") or process.get("description") or "")
                except (OSError, ValueError, SystemExit):
                    pass
            candidates.append(item)
        return {
            "id": str(current.get("id") or ""),
            "stage_count": len(current.get("stages") or []) if isinstance(current.get("stages"), list) else 0,
            "default": str(selection.get("default") or ""),
            "allowed": candidates,
        }
