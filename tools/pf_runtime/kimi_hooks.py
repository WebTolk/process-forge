"""Thin Kimi Code lifecycle-hook adapter for the local PF Runtime.

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
    "SessionStart": {
        "startup": "agent.session.started",
        "resume": "agent.session.resumed",
        "clear": "agent.session.started",
        "compact": "agent.session.compacted",
        "default": "agent.session.started",
    },
    "SessionEnd": {"default": "agent.session.ended"},
    "PreCompact": {"default": "agent.session.compaction.started"},
    "PostCompact": {"default": "agent.session.compacted"},
    "PostToolUse": {"default": "agent.command.completed"},
    "PreToolUse": {"default": "agent.command.started"},
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


def _event_name(payload: dict[str, Any]) -> str:
    """Resolve the native event name from a Kimi Code hook payload."""
    for key in ("hook_event_name", "event", "event_name", "hook"):
        value = payload.get(key)
        if isinstance(value, str) and value:
            return value
    return ""


def _session_id(payload: dict[str, Any]) -> str:
    for key in ("session_id", "sessionId", "sid"):
        value = payload.get(key)
        if isinstance(value, str) and value:
            return value
    return ""


def _project_ref(payload: dict[str, Any]) -> str:
    for key in ("cwd", "project_root", "projectRoot", "workspace", "project"):
        value = payload.get(key)
        if isinstance(value, str) and value:
            return value
    return ""


def _source(payload: dict[str, Any]) -> str:
    value = payload.get("source")
    if isinstance(value, str) and value:
        return value
    return "startup"


def normalized_event(payload: dict[str, Any]) -> dict[str, Any] | None:
    hook = _event_name(payload)
    mapping = EVENTS.get(hook)
    if not mapping:
        return None
    source = _source(payload)
    event_type = mapping.get(source) or mapping.get("default")
    cwd = _project_ref(payload)
    session_id = _session_id(payload)
    if not event_type or not cwd or not session_id:
        return None
    tool_name = str(payload.get("tool_name") or "")
    data = {
        key: payload[key]
        for key in (
            "turn_id",
            "tool_name",
            "tool_use_id",
            "model",
            "permission_mode",
            "reason",
        )
        if payload.get(key) not in (None, "")
    }
    if hook == "PostToolUse" and tool_name and tool_name != "Bash":
        event_type = "agent.tool.completed"
    event_id = f"kimi:{hook}:{session_id}:{payload.get('turn_id', '')}:{payload.get('tool_use_id', '')}"
    if hook == "SessionStart" and source != "startup":
        event_id += f":{source}"
    return {
        "schema_version": 1,
        "event_type": event_type,
        "event_id": event_id,
        "project_root": cwd,
        "session_id": session_id,
        "agent_id": "kimi",
        "source": {"adapter": "kimi-hooks", "agent": "kimi", "session_id": session_id},
        "payload": data,
    }


def native_envelope(payload: dict[str, Any]) -> dict[str, Any] | None:
    """Build a raw Kimi envelope; mapping stays in this thin adapter."""
    cwd = _project_ref(payload)
    hook = _event_name(payload) or "Unknown"
    if not cwd:
        return None
    envelope: dict[str, Any] = {
        "provider": "kimi",
        "adapter": "kimi-hooks",
        "native_event_type": hook,
        "native_event_id": None,
        "native_id_scope": "session",
        "native_event_id_stable": False,
        "source_session_id": _session_id(payload) or None,
        "source_project_ref": cwd,
        "payload_version": "kimi-hooks.v1",
        "raw_payload": dict(payload),
        "derived_event": normalized_event(payload),
    }
    prompt = payload.get("prompt")
    if (
        hook == "UserPromptSubmit"
        and isinstance(prompt, str)
        and prompt.strip()
        and envelope["source_session_id"]
    ):
        envelope["derived_conversation_messages"] = [
            {
                "message_role": "user",
                "participant": {"id": "operator", "type": "human", "role": "operator"},
                "session_id": envelope["source_session_id"],
                "turn_id": str(payload.get("turn_id") or "") or None,
                "content": prompt,
                "content_source": {
                    "kind": "kimi_hook",
                    "provider": "kimi",
                    "adapter": "kimi-hooks",
                    "native_event_type": "UserPromptSubmit",
                    "content_provenance": "provider_payload",
                },
                "delivery": {"state": "complete", "sequence": 0, "final": True},
            }
        ]
    assistant_message = payload.get("last_assistant_message")
    if (
        hook in {"Stop", "SubagentStop", "SessionEnd"}
        and isinstance(assistant_message, str)
        and assistant_message.strip()
        and envelope["source_session_id"]
    ):
        is_subagent = hook == "SubagentStop"
        agent_id = str(payload.get("agent_id") or "")
        participant_id = (
            f"subagent:{agent_id}"
            if is_subagent and agent_id
            else ("subagent" if is_subagent else "kimi")
        )
        messages = envelope.setdefault("derived_conversation_messages", [])
        assert isinstance(messages, list)
        messages.append(
            {
                "message_role": "assistant",
                "participant": {
                    "id": participant_id,
                    "type": "subagent" if is_subagent else "agent",
                    "role": "subagent" if is_subagent else "assistant",
                },
                "session_id": envelope["source_session_id"],
                "turn_id": str(payload.get("turn_id") or "") or None,
                "content": assistant_message,
                "content_source": {
                    "kind": "kimi_hook",
                    "provider": "kimi",
                    "adapter": "kimi-hooks",
                    "native_event_type": hook,
                    "content_provenance": "provider_payload",
                },
                "delivery": {"state": "complete", "sequence": 1, "final": True},
            }
        )
    return envelope


def dispatch(payload: dict[str, Any]) -> dict[str, Any]:
    project_ref = _project_ref(payload)
    if not project_ref:
        return {"status": "ignored"}
    runtime = runtime_bootstrap()
    core = runtime.core
    host = runtime.host
    service = runtime.service
    project_root = Path(project_ref).expanduser()
    try:
        from processforge_core.work.consistency import RunTaskInputReader

        RunTaskInputReader().require_flow_root(project_root)
    except SystemExit:
        return {"status": "ignored", "reason": "not_processforge_project"}

    workplace_root = core.resolve_workplace_root(None, project_root=project_root)
    _configuration, collect = host.hook_configuration(
        project_root, workplace_root, core
    )
    if not collect:
        return host.ignored_hook()
    envelope = native_envelope(payload)
    if not envelope:
        return {"status": "ignored"}
    try:
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            exit_code = service.runtime_request(
                argparse.Namespace(workplace=str(workplace_root), json=True),
                core,
                "/event",
                envelope,
            )
        if exit_code == 0:
            body = json.loads(output.getvalue()) if output.getvalue().strip() else {}
            if isinstance(body, dict) and body.get("routing_status") in {
                "ignored",
                "denied",
            }:
                return {**body, "status": "ignored", "transport": "runtime"}
            return {"status": "delivered", "transport": "runtime"}
    except (OSError, SystemExit, ValueError):
        pass

    with contextlib.redirect_stdout(io.StringIO()):
        result = host.ingest_event(envelope, None, core)
    if result.get("routing_status") in {"ignored", "denied"}:
        return {**result, "status": "ignored", "transport": "ledger-fallback"}
    return {"status": "delivered", "transport": "ledger-fallback", **result}


def main() -> int:
    src_root = str(Path(__file__).resolve().parents[2] / "src")
    if src_root not in sys.path:
        sys.path.insert(0, src_root)
    from processforge_core import diagnostics

    hook = ""
    debug = os.environ.get("PF_KIMI_HOOK_DEBUG") == "1"
    options = (
        diagnostics.invocation_options("diagnostic", sink="stderr") if debug else {}
    )
    logger = diagnostics.for_project(Path.cwd(), invocation=options)
    if logger is diagnostics.NULL and (debug or os.environ.get("PF_DIAGNOSTICS")):
        logger = diagnostics.for_stderr(options)
    try:
        payload = json.load(sys.stdin)
        hook = _event_name(payload) if isinstance(payload, dict) else ""
        if (
            isinstance(payload, dict)
            and isinstance(_project_ref(payload), str)
            and _project_ref(payload)
        ):
            logger = diagnostics.for_project(
                Path(_project_ref(payload)),
                session_id=_session_id(payload),
                invocation=options,
            )
            if logger is diagnostics.NULL and (
                debug or os.environ.get("PF_DIAGNOSTICS")
            ):
                logger = diagnostics.for_stderr(options)
        with diagnostics.operation(
            logger,
            "hooks",
            "hook.dispatch",
            session_id=_session_id(payload) if isinstance(payload, dict) else None,
            build=diagnostics.identity_for(logger, __file__),
        ):
            result = dispatch(payload if isinstance(payload, dict) else {})
        hook = _event_name(payload) if isinstance(payload, dict) else ""
        if hook in {"Stop", "SubagentStop"}:
            print("{}")
        elif hook == "SessionStart" and result.get("status") == "delivered":
            session_id = _session_id(payload)
            print(
                json.dumps(
                    {
                        "hookSpecificOutput": {
                            "hookEventName": "SessionStart",
                            "additionalContext": f"ProcessForge session id: {session_id}. Use it only with pf.session_* tools for this project.",
                        }
                    },
                    ensure_ascii=False,
                )
            )
        logger.debug(
            "hook.result",
            {
                "status": result.get("status"),
                "transport": result.get("transport"),
                "reason": result.get("reason"),
                "normalized_event_count": len(result.get("normalized_event_ids") or []),
            },
            component="hooks",
            code="hook.result",
        )
    except Exception as exc:
        if hook in {"Stop", "SubagentStop"}:
            print("{}")
        logger.error(
            "hook.ignored", {"exception": exc}, component="hooks", code="hook.ignored"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
