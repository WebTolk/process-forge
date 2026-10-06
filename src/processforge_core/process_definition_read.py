"""Existing effective process read rules with explicit dependencies."""

from __future__ import annotations

import copy
from dataclasses import dataclass
from typing import Any, Callable

__all__ = ()


@dataclass(frozen=True)
class ProcessDefinitionReadService:
    resolve_definition: Callable[[str], dict[str, Any]]
    fingerprint: Callable[[dict[str, Any]], str]

    def effective_process(self, run: dict[str, Any]) -> tuple[dict[str, Any], str]:
        pin = run.get("process_execution") if isinstance(run.get("process_execution"), dict) else {}
        definition = pin.get("definition") if isinstance(pin.get("definition"), dict) else None
        if definition is not None and str(pin.get("process_fingerprint") or "") == self.fingerprint(definition):
            return copy.deepcopy(definition), "pinned"
        if pin:
            return copy.deepcopy(definition) if isinstance(definition, dict) else {"id": str(run.get("process") or ""), "stages": []}, "corrupt"
        try:
            definition = self.resolve_definition(str(run.get("process") or ""))
            return copy.deepcopy(definition), "legacy_unpinned"
        except (OSError, SystemExit, ValueError):
            return {"id": str(run.get("process") or ""), "stages": []}, "missing"
