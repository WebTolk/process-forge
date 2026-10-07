"""Optional host-integration status adapters for generic project services."""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any


_STATUS_VALUES = {"installed", "missing", "stale", "invalid", "unavailable", "unsupported"}
_TOKEN = re.compile(r"^[a-zA-Z][a-zA-Z0-9_.-]{0,63}$")
_EVENT_TOKEN = re.compile(r"^[A-Za-z][A-Za-z0-9_.-]{0,63}$")


def optional_host_integration_status(project_root: Path, core: Any) -> dict[str, Any]:
    """Return bounded optional Codex telemetry without affecting generic status.

    The legacy ``codex_integration`` read-model is retained, but absence or a
    bounded optional callback failure cannot block project initialization.
    Exception messages and arbitrary callback fields are deliberately omitted.
    """
    base: dict[str, Any] = {
        "status": "unavailable",
        "required": False,
        "severity": "info",
        "purpose": "optional_host_telemetry",
        "error": "optional_integration_unavailable",
    }
    callback = getattr(core, "project_codex_integration_status", None)
    if not callable(callback):
        return base
    try:
        raw = callback(Path(project_root).expanduser().resolve())
    except (Exception, SystemExit):
        return base
    if not isinstance(raw, dict):
        return {**base, "error": "optional_integration_result_invalid"}

    status = raw.get("status")
    if not isinstance(status, str) or status not in _STATUS_VALUES:
        return {**base, "error": "optional_integration_result_invalid"}
    result: dict[str, Any] = {**base, "status": status}
    if status != "unavailable":
        result.pop("error", None)
    target = raw.get("target")
    if target == ".codex/hooks.json":
        result["target"] = target
    adapter = raw.get("adapter")
    if (isinstance(adapter, str) and adapter and len(adapter) <= 256
            and not Path(adapter).is_absolute() and ".." not in Path(adapter).parts
            and not re.match(r"^[A-Za-z]:", adapter)):
        result["adapter"] = adapter.replace("\\", "/")
    for key in ("event_types", "registered_events", "missing_events"):
        values = raw.get(key)
        if isinstance(values, list) and len(values) <= 64 and all(isinstance(item, str) and _EVENT_TOKEN.fullmatch(item) for item in values):
            result[key] = sorted(set(values))
    global_hooks = raw.get("global_hooks")
    if isinstance(global_hooks, dict) and all(type(global_hooks.get(key)) is bool for key in ("exists", "managed")):
        result["global_hooks"] = {"exists": global_hooks["exists"], "managed": global_hooks["managed"]}
    if type(raw.get("restart_required")) is bool:
        result["restart_required"] = raw["restart_required"]
    if raw.get("scope") == "project-local":
        result["scope"] = "project-local"
    error = raw.get("error")
    if isinstance(error, str) and _TOKEN.fullmatch(error):
        result["error"] = error
    return result


__all__ = ["optional_host_integration_status"]
