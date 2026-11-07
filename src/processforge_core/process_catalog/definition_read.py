"""Existing effective process read rules with explicit dependencies."""

from __future__ import annotations

import copy
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ..process_execution import canonical_fingerprint
from .catalog_read import ProcessCatalogReadService

__all__ = ()


@dataclass(frozen=True)
class ProcessDefinitionReadService:
    project_root: Path
    catalog: ProcessCatalogReadService | None = field(default=None, kw_only=True)

    def effective_process(self, run: dict[str, Any]) -> tuple[dict[str, Any], str]:
        pin_value = run.get("process_execution")
        pin = pin_value if isinstance(pin_value, dict) else {}
        definition_value = pin.get("definition")
        definition = definition_value if isinstance(definition_value, dict) else None
        if definition is not None and str(
            pin.get("process_fingerprint") or ""
        ) == canonical_fingerprint(definition):
            return copy.deepcopy(definition), "pinned"
        if pin:
            return copy.deepcopy(definition) if isinstance(definition, dict) else {
                "id": str(run.get("process") or ""),
                "stages": [],
            }, "corrupt"
        try:
            catalog = (
                self.catalog
                if self.catalog is not None
                else ProcessCatalogReadService(self.project_root)
            )
            definition = catalog.resolve_definition(
                str(run.get("process") or "")
            ).process
            return copy.deepcopy(definition), "legacy_unpinned"
        except (OSError, SystemExit, ValueError):
            return {"id": str(run.get("process") or ""), "stages": []}, "missing"
