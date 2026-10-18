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
        pin = run.get("process_execution") if isinstance(run.get("process_execution"), dict) else {}
        definition = pin.get("definition") if isinstance(pin.get("definition"), dict) else None
        if definition is not None and str(pin.get("process_fingerprint") or "") == canonical_fingerprint(definition):
            return copy.deepcopy(definition), "pinned"
        if pin:
            return copy.deepcopy(definition) if isinstance(definition, dict) else {"id": str(run.get("process") or ""), "stages": []}, "corrupt"
        try:
            catalog = self.catalog if self.catalog is not None else ProcessCatalogReadService(self.project_root)
            definition = catalog.resolve_definition(str(run.get("process") or "")).process
            return copy.deepcopy(definition), "legacy_unpinned"
        except (OSError, SystemExit, ValueError):
            return {"id": str(run.get("process") or ""), "stages": []}, "missing"
