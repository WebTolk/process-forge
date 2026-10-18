from __future__ import annotations

from typing import Any


PROCESS_COORDINATION_MODES = {"simple_allowed", "organized_required", "organized_optional"}


def process_coordination_requirements(process_data: dict[str, Any]) -> dict[str, Any]:
    raw = process_data.get("coordination_requirements") if isinstance(process_data.get("coordination_requirements"), dict) else {}
    mode = str(raw.get("mode") or "simple_allowed")
    if mode not in PROCESS_COORDINATION_MODES:
        mode = "simple_allowed"
    return {
        "mode": mode,
        "director_inbox": raw.get("director_inbox") if isinstance(raw.get("director_inbox"), dict) else {"required": False, "optional": False},
        "error_workflow": raw.get("error_workflow") if isinstance(raw.get("error_workflow"), dict) else {"mode": "none"},
    }
