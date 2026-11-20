"""Adapt an explicitly applied workplace request to the common index owner."""

from __future__ import annotations

import argparse
import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

from processforge_core.resources.index_maintenance import (
    WorkplaceIndexMaintenanceService,
)


class WorkplaceIndexMaintenanceCommand:
    """Invoke workplace maintenance only after the explicit apply guard."""

    def __init__(
        self,
        *,
        maintenance_factory: Callable[
            [Path], WorkplaceIndexMaintenanceService
        ] = WorkplaceIndexMaintenanceService,
    ) -> None:
        """Save a cold factory; distribution overrides belong in its composition."""
        self._maintenance_factory = maintenance_factory

    def execute(self, args: argparse.Namespace) -> int:
        """Print a safe maintenance report; return zero only for a successful pass."""
        if not getattr(args, "apply", False):
            payload = self._failure("search_maintenance_apply_required")
        elif not getattr(args, "workplace", None):
            payload = self._failure("search_maintenance_workplace_required")
        else:
            try:
                workplace = Path(args.workplace).expanduser().resolve()
                payload = self._maintenance_factory(workplace).run(reason="manual")
            except Exception:
                # The canonical service returns bounded operation failures.
                # Also keep factory/path errors off this new public surface.
                payload = self._failure("search_maintenance_failed")
        rows = payload.get("results")
        success = (
            isinstance(rows, list)
            and bool(rows)
            and all(isinstance(row, dict) and row.get("status") == "ok" for row in rows)
        )
        if getattr(args, "json", False):
            print(
                json.dumps(payload, ensure_ascii=True, sort_keys=True, allow_nan=False)
            )
        else:
            print(f"STATUS: {'ok' if success else 'failed'}")
            for row in rows if isinstance(rows, list) else []:
                print(f"SEARCH_INDEX: {row.get('search_status') or 'unavailable'}")
                if row.get("action"):
                    print(f"ACTION: {row['action']}")
                if row.get("error"):
                    print(f"ERROR: {row['error']}")
            if payload.get("report"):
                print(f"REPORT: {payload['report']}")
        return 0 if success else 1

    @staticmethod
    def _failure(code: str) -> dict[str, Any]:
        return {
            "schema_version": 1,
            "kind": "pf.search_index.maintenance",
            "scope": "workplace",
            "reason": "manual",
            "project_count": 0,
            "results": [{"scope": "workplace", "status": "error", "error": code}],
            "report": None,
        }
