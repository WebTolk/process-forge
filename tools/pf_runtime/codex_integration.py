"""Opt-in installer/status/remover for project-local ProcessForge Codex hooks.

It deliberately manages only ``<project>/.codex/hooks.json``.  Codex host MCP
configuration belongs to the user's Codex configuration and is documented,
not silently edited by this project utility.
"""

from __future__ import annotations

import argparse
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


EVENTS = ("SessionStart", "SessionEnd", "PostToolUse", "UserPromptSubmit", "PreCompact", "PostCompact", "Stop", "SubagentStop")


def hook_command(adapter: Path) -> str:
    # Codex runs hook commands with the session cwd, so use an absolute path.
    return f'py -3 "{adapter}"'


def managed_handler(adapter: Path, event: str) -> dict[str, Any]:
    command = hook_command(adapter)
    handler: dict[str, Any] = {"type": "command", "command": command, "commandWindows": command, "timeout": 3, "statusMessage": "Recording ProcessForge session facts"}
    # Observation must not hold up high-frequency tool calls. Codex keeps
    # SessionEnd synchronous by contract, so do not claim otherwise there.
    if event != "SessionEnd":
        handler["async"] = True
    return handler


def load_config(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {"description": "ProcessForge Codex observation hooks", "hooks": {}}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SystemExit("FAIL: existing hooks.json is not valid JSON; no changes were made") from exc
    if not isinstance(value, dict) or not isinstance(value.get("hooks", {}), dict):
        raise SystemExit("FAIL: existing hooks.json has no object hooks field; no changes were made")
    value.setdefault("hooks", {})
    return value


def is_managed(handler: Any, adapter: Path) -> bool:
    return isinstance(handler, dict) and str(handler.get("commandWindows") or "") == hook_command(adapter)


def install_payload(current: dict[str, Any], adapter: Path) -> tuple[dict[str, Any], list[str]]:
    result = json.loads(json.dumps(current))
    hooks = result.setdefault("hooks", {})
    changed: list[str] = []
    for event in EVENTS:
        groups = hooks.setdefault(event, [])
        if not isinstance(groups, list):
            raise SystemExit(f"FAIL: hooks.{event} is not an array; no changes were made")
        matching = next((group for group in groups if isinstance(group, dict) and str(group.get("matcher") or "") == ""), None)
        if matching is None:
            matching = {"hooks": []}
            groups.append(matching)
        handlers = matching.setdefault("hooks", [])
        if not isinstance(handlers, list):
            raise SystemExit(f"FAIL: hooks.{event}.hooks is not an array; no changes were made")
        if not any(is_managed(item, adapter) for item in handlers):
            handlers.append(managed_handler(adapter, event))
            changed.append(event)
    return result, changed


def remove_payload(current: dict[str, Any], adapter: Path) -> tuple[dict[str, Any], list[str]]:
    result = json.loads(json.dumps(current))
    hooks = result.get("hooks") if isinstance(result.get("hooks"), dict) else {}
    changed: list[str] = []
    for event in list(hooks):
        groups = hooks[event]
        if not isinstance(groups, list):
            continue
        retained_groups: list[Any] = []
        for group in groups:
            if not isinstance(group, dict) or not isinstance(group.get("hooks"), list):
                retained_groups.append(group)
                continue
            handlers = [item for item in group["hooks"] if not is_managed(item, adapter)]
            if len(handlers) != len(group["hooks"]):
                changed.append(event)
            if handlers:
                retained_groups.append({**group, "hooks": handlers})
        if retained_groups:
            hooks[event] = retained_groups
        else:
            hooks.pop(event, None)
    return result, sorted(set(changed))


def write_atomic(path: Path, payload: dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    backup = path.with_name(path.name + ".pf-backup-" + datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S%f"))
    if path.exists():
        shutil.copy2(path, backup)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)
    return backup if backup.exists() else Path()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("status", "install", "remove"))
    parser.add_argument("--project-root", required=True)
    parser.add_argument("--adapter", default=str(Path(__file__).with_name("codex_hooks.py").resolve()))
    parser.add_argument("--apply", action="store_true", help="write the project-local hooks.json; otherwise show a dry run")
    args = parser.parse_args()
    project = Path(args.project_root).expanduser().resolve()
    target = project / ".codex" / "hooks.json"
    adapter = Path(args.adapter).expanduser().resolve()
    if not adapter.is_file():
        raise SystemExit("FAIL: adapter path does not exist")
    current = load_config(target)
    if args.action == "status":
        installed = [event for event, groups in current.get("hooks", {}).items() if isinstance(groups, list) and any(isinstance(group, dict) and any(is_managed(item, adapter) for item in group.get("hooks", []) if isinstance(group.get("hooks", []), list)) for group in groups)]
        print(json.dumps({"status": "ok", "target": str(target), "adapter": str(adapter), "registered_events": sorted(installed), "complete": set(installed) == set(EVENTS)}, ensure_ascii=False))
        return 0
    payload, changed = install_payload(current, adapter) if args.action == "install" else remove_payload(current, adapter)
    result: dict[str, Any] = {"action": args.action, "target": str(target), "adapter": str(adapter), "changed_events": changed, "applied": bool(args.apply)}
    if args.apply and changed:
        backup = write_atomic(target, payload)
        result["backup"] = str(backup) if backup else None
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
