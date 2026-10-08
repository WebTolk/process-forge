"""Project coordination mode read model with an explicit snapshot dependency."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ..ports import ProjectSnapshotReadPort


@dataclass(frozen=True)
class GarageModeService:
    project_root: Path
    workplace_root: Path
    snapshots: ProjectSnapshotReadPort = field(kw_only=True, repr=False, compare=False)

    def status(self, *, snapshot: dict[str, Any] | None = None, session_id: str = "") -> dict[str, Any]:
        snapshot = snapshot or self.snapshots.load()
        coordination = snapshot.get("workplace_coordination") if isinstance(snapshot.get("workplace_coordination"), dict) else {}
        effective_mode = str(coordination.get("effective_mode") or "simple")
        director_required = bool(coordination.get("director_required", effective_mode == "organized"))
        mode = "forge" if effective_mode == "organized" or director_required else "garage"
        blockers: list[dict[str, str]] = []
        if mode == "forge" and director_required and not bool(coordination.get("director_office_exists", False)):
            blockers.append({"code": "forge_runtime_required_but_unavailable", "message": "Project coordination requires Forge/Director runtime, but required runtime infrastructure is unavailable."})
        return {
            "mode": mode,
            "source": "project_coordination",
            "coordination": {
                "effective_mode": effective_mode,
                "director_required": director_required,
                "director_available_at_workplace": bool(coordination.get("director_available_at_workplace", False)),
                "director_office_exists": bool(coordination.get("director_office_exists", False)),
            },
            "session": {"status": "bound", "id": session_id} if session_id else {"status": "absent"},
            "blockers": blockers,
        }
