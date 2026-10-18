"""Existing context reconciliation projection through an explicit checker."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

from .context_read import ProjectContextCheck


@dataclass(frozen=True)
class ContextReconciliationService:
    project_root: Path
    workplace_root: Path
    context_checker: Callable[[], ProjectContextCheck] = field(kw_only=True, repr=False, compare=False)

    def status(self) -> dict[str, Any]:
        check = self.context_checker()(self.project_root, explicit_workplace=str(self.workplace_root))
        stale_reasons = [str(item.get("reason") or "") for item in check.get("stale_resources", []) if isinstance(item, dict)]
        technical_only = bool(stale_reasons) and all(reason in {"valid_until expired"} or reason.startswith("source changed:") for reason in stale_reasons)
        return {
            "status": check.get("status"),
            "safe_automatic_refresh": bool(check.get("stale")) and technical_only,
            "operator_decision_required": bool(check.get("broken")) or (bool(check.get("stale")) and not technical_only),
            "reasons": stale_reasons,
        }
