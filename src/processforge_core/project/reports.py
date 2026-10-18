"""Derived report status through explicit live snapshot and path dependencies."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ..ports import ProjectSnapshotReadPort

DERIVED_REPORTS = [
    Path("artifacts/project-classification-report.md"),
    Path("artifacts/global-resource-matching-report.md"),
    Path("artifacts/toolchain-detection-report.md"),
    Path("artifacts/capability-provider-audit.md"),
    Path("artifacts/project-profile.md"),
]


@dataclass(frozen=True)
class DerivedReportLifecycleService:
    snapshots: ProjectSnapshotReadPort = field(kw_only=True)
    flow_root: Callable[[], Path] = field(kw_only=True)

    def status(self, *, snapshot: dict[str, Any] | None = None) -> dict[str, Any]:
        snapshot = snapshot or self.snapshots.load()
        snapshot_time = str((snapshot.get("snapshot") if isinstance(snapshot.get("snapshot"), dict) else {}).get("generated_at") or snapshot.get("generated_at") or "")
        flow_root = self.flow_root()
        reports = []
        for rel_path in DERIVED_REPORTS:
            path = flow_root / rel_path
            status = "missing"
            if path.is_file():
                status = "current"
                if snapshot_time:
                    try:
                        import datetime as _dt

                        generated = _dt.datetime.fromisoformat(snapshot_time.replace("Z", "+00:00")).timestamp()
                        if path.stat().st_mtime < generated:
                            status = "stale"
                    except (OSError, ValueError):
                        status = "historical"
            reports.append({"path": f".pf/{rel_path.as_posix()}", "status": status})
        aggregate = "stale" if any(item["status"] == "stale" for item in reports) else ("missing" if any(item["status"] == "missing" for item in reports) else "current")
        return {"status": aggregate, "snapshot_generated_at": snapshot_time, "reports": reports}
