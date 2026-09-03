"""Thin Codex lifecycle-hook adapter for the local PF Runtime.

It converts documented hook facts into normalized events and deliberately
returns success when the current directory is not a ProcessForge project.
"""

from __future__ import annotations

import argparse
import contextlib
import importlib.util
import io
import json
import os
import sys
from pathlib import Path
from typing import Any

_RUNTIME_BOOTSTRAP: Any | None = None

EVENTS = {
    "SessionStart": {"startup": "agent.session.started", "resume": "agent.session.resumed", "clear": "agent.session.started", "compact": "agent.session.compacted"},
    "SessionEnd": {"default": "agent.session.ended"},
    "PreCompact": {"default": "agent.session.compaction.started"},
    "PostCompact": {"default": "agent.session.compacted"},
    "PostToolUse": {"default": "agent.command.completed"},
}


def runtime_bootstrap() -> Any:
    global _RUNTIME_BOOTSTRAP
    if _RUNTIME_BOOTSTRAP is None:
        repo_root = Path(__file__).resolve().parents[2]
        module_name = "processforge_core.bootstrap"
        module = sys.modules.get(module_name)
        if module is None:
            bootstrap_path = repo_root / "src" / "processforge_core" / "bootstrap.py"
            spec = importlib.util.spec_from_file_location(module_name, bootstrap_path)
            if spec is None or spec.loader is None:
                raise ImportError(f"could not load bootstrap module: {bootstrap_path}")
            module = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = module
            spec.loader.exec_module(module)
        _RUNTIME_BOOTSTRAP = module.bootstrap_runtime(__file__)
    return _RUNTIME_BOOTSTRAP


def normalized_event(payload: dict[str, Any]) -> dict[str, Any] | None:
    hook = str(payload.get("hook_event_name") or "")
    mapping = EVENTS.get(hook)
    if not mapping:
        return None
    source = str(payload.get("source") or "startup")
    event_type = mapping.get(source) or mapping.get("default")
    cwd = str(payload.get("cwd") or "")
    session_id = str(payload.get("session_id") or "")
    if not event_type or not cwd or not session_id:
        return None
    tool_name = str(payload.get("tool_name") or "")
    data = {key: payload[key] for key in ("turn_id", "tool_name", "tool_use_id", "model", "permission_mode", "reason") if payload.get(key) not in (None, "")}
    if hook == "PostToolUse" and tool_name and tool_name != "Bash":
        event_type = "agent.tool.completed"
    return {
        "schema_version": 1,
        "event_type": event_type,
        "event_id": f"codex:{hook}:{session_id}:{payload.get('turn_id', '')}:{payload.get('tool_use_id', '')}",
        "project_root": cwd,
        "session_id": session_id,
        "agent_id": "codex",
        "source": {"adapter": "codex-hooks", "agent": "codex", "session_id": session_id},
        "payload": data,
    }


def native_envelope(payload: dict[str, Any]) -> dict[str, Any] | None:
    """Build a raw Codex envelope; mapping stays in this thin adapter."""

    cwd = str(payload.get("cwd") or "")
    hook = str(payload.get("hook_event_name") or "Unknown")
    if not cwd:
        return None
    envelope = {
        "provider": "codex",
        "adapter": "codex-hooks",
        "native_event_type": hook,
        # Codex hook input has no documented stable delivery identifier.
        "native_event_id": None,
        "native_id_scope": "session",
        "native_event_id_stable": False,
        "source_session_id": str(payload.get("session_id") or "") or None,
        "source_project_ref": cwd,
        "payload_version": "codex-hooks.v1",
        "raw_payload": dict(payload),
        # Existing normalization is deliberately attached rather than moved
        # into Host/Core, so other providers need no core changes.
        "derived_event": normalized_event(payload),
    }
    prompt = payload.get("prompt")
    if hook == "UserPromptSubmit" and isinstance(prompt, str) and prompt.strip() and envelope["source_session_id"]:
        envelope["derived_conversation_messages"] = [
            {
                "message_role": "user",
                "participant": {"id": "operator", "type": "human", "role": "operator"},
                "session_id": envelope["source_session_id"],
                "turn_id": str(payload.get("turn_id") or "") or None,
                "content": prompt,
                "content_source": {
                    "kind": "codex_hook",
                    "provider": "codex",
                    "adapter": "codex-hooks",
                    "native_event_type": "UserPromptSubmit",
                    "content_provenance": "provider_payload",
                },
                "delivery": {"state": "complete", "sequence": 0, "final": True},
            }
        ]
    assistant_message = payload.get("last_assistant_message")
    if hook in {"Stop", "SubagentStop", "SessionEnd"} and isinstance(assistant_message, str) and assistant_message.strip() and envelope["source_session_id"]:
        is_subagent = hook == "SubagentStop"
        agent_id = str(payload.get("agent_id") or "")
        participant_id = f"subagent:{agent_id}" if is_subagent and agent_id else ("subagent" if is_subagent else "codex")
        envelope.setdefault("derived_conversation_messages", []).append(
            {
                "message_role": "assistant",
                "participant": {"id": participant_id, "type": "subagent" if is_subagent else "agent", "role": "subagent" if is_subagent else "assistant"},
                "session_id": envelope["source_session_id"],
                "turn_id": str(payload.get("turn_id") or "") or None,
                "content": assistant_message,
                "content_source": {
                    "kind": "codex_hook",
                    "provider": "codex",
                    "adapter": "codex-hooks",
                    "native_event_type": hook,
                    "content_provenance": "provider_payload",
                },
                "delivery": {"state": "complete", "sequence": 1, "final": True},
            }
        )
    return envelope


def dispatch(payload: dict[str, Any]) -> dict[str, Any]:
    envelope = native_envelope(payload)
    if not envelope:
        return {"status": "ignored"}
    runtime = runtime_bootstrap()
    core = runtime.core
    host = runtime.host
    service = runtime.service
    project_root = Path(str(envelope["source_project_ref"])).expanduser()
    try:
        core.require_flow_root(project_root)
    except SystemExit:
        return {"status": "ignored", "reason": "not_processforge_project"}

    # Prefer the active Runtime so hook delivery shares its authenticated IPC,
    # lifecycle record and operator journal.  A hook must remain advisory: an
    # unavailable daemon must not fail or delay the Codex turn, so fall back to
    # the durable Host/Core path that was used before the daemon was started.
    workplace_root = core.resolve_workplace_root(None, project_root=project_root)
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            exit_code = service.runtime_request(
                argparse.Namespace(workplace=str(workplace_root), json=True),
                core,
                "/event",
                envelope,
            )
        if exit_code == 0:
            return {"status": "delivered", "transport": "runtime"}
    except (OSError, SystemExit, ValueError):
        pass

    with contextlib.redirect_stdout(io.StringIO()):
        result = host.ingest_event(envelope, None, core)
    return {"status": "delivered", "transport": "ledger-fallback", **result}


def main() -> int:
    try:
        payload = json.load(sys.stdin)
        result = dispatch(payload if isinstance(payload, dict) else {})
        # Stop and SubagentStop require a JSON result on stdout.  An empty
        # object is a neutral protocol response: this observer never blocks,
        # rewrites, or continues a Codex session.
        hook = str(payload.get("hook_event_name") or "") if isinstance(payload, dict) else ""
        if hook in {"Stop", "SubagentStop"}:
            print("{}")
        elif hook == "SessionStart" and result.get("status") == "delivered":
            session_id = str(payload.get("session_id") or "")
            # This is a non-controlling handoff of the already Ledger-bound
            # identifier.  It lets the current Codex turn call session MCP
            # tools without searching private PF state or guessing a path.
            print(json.dumps({"hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": f"ProcessForge session id: {session_id}. Use it only with pf.session_* tools for this project."}}, ensure_ascii=False))
        if os.environ.get("PF_CODEX_HOOK_DEBUG") == "1":
            # Never append diagnostic output to Codex hook protocol stdout.
            print(json.dumps(result, ensure_ascii=False), file=sys.stderr)
    except Exception as exc:  # hooks are observation, never a Codex failure point
        if os.environ.get("PF_CODEX_HOOK_DEBUG") == "1":
            print(json.dumps({"status": "ignored", "reason": type(exc).__name__}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
