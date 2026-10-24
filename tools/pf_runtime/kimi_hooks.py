"""Observe Kimi Code 2.3 native hooks without blocking the host.

Capture real text parts and subagent responses. Stop/SessionEnd do not carry
the main assistant's answer. Other content remains in the private raw journal.
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

# Capture the stdlib-only native leaf before any Core/adapter import. Python's
# -B flag does not prevent execution of an existing unchecked bytecode cache.
_native_root = Path(__file__).absolute().parents[2]
_native_module = sys.modules.get("pf_native_control")
if _native_module is None:
    _native_path = _native_root / "tools/pf_native_control.py"
    _native_source = _native_path.read_bytes()
    _native_module = type(sys)("pf_native_control")
    _native_module.__file__ = str(_native_path)
    setattr(_native_module, "_captured_source", _native_source)
    sys.modules["pf_native_control"] = _native_module
    exec(
        compile(_native_source, str(_native_path), "exec", dont_inherit=True),
        _native_module.__dict__,
    )
_captured_native_source = getattr(_native_module, "_captured_source", None)
if not isinstance(_captured_native_source, bytes):
    # A previously imported unsealed library is a supported source-mode caller.
    # It cannot promote itself to a sealed publication via its current-file hash.
    if getattr(_native_module, "_PUBLICATION_SEAL", None) is not None:
        raise getattr(_native_module, "NativeControlError")()
    _native_entry = None
else:
    _native_entry = getattr(_native_module, "bootstrap_entry")(
        _native_root, trusted_leaf=_captured_native_source
    )


if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pf_runtime.raw_ingress_kernel import raw_payload_hash  # noqa: E402

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
    "PostToolUseFailure": {"default": "agent.command.completed"},
    "PreToolUse": {"default": "agent.command.started"},
}
SUPPORTED_HOOKS = frozenset(EVENTS) | {"UserPromptSubmit", "Stop", "SubagentStop"}


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


def _string(payload: dict[str, Any], key: str) -> str:
    value = payload.get(key)
    return value if isinstance(value, str) and value.strip() else ""


def _event_name(payload: dict[str, Any]) -> str:
    """Read the native snake_case field, without guessing other providers."""
    return _string(payload, "hook_event_name")


def _session_id(payload: dict[str, Any]) -> str:
    return _string(payload, "session_id")


def _project_ref(payload: dict[str, Any]) -> str:
    return _string(payload, "cwd")


def _source(payload: dict[str, Any]) -> str:
    return _string(payload, "source") or "startup"


def _text(content: Any) -> str:
    """Extract provider text, leaving non-text content in the raw payload."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "".join(
            part["text"]
            for part in content
            if isinstance(part, dict)
            and part.get("type") == "text"
            and isinstance(part.get("text"), str)
        )
    return ""


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
    tool_name = _string(payload, "tool_name")
    data = {
        key: payload[key]
        for key in (
            "turn_id",
            "tool_name",
            "tool_call_id",
            "model",
            "permission_mode",
            "reason",
            "trigger",
            "token_count",
            "estimated_token_count",
        )
        if payload.get(key) not in (None, "")
    }
    if hook in {"PreToolUse", "PostToolUse", "PostToolUseFailure"}:
        if tool_name and tool_name != "Bash":
            event_type = (
                "agent.tool.started" if hook == "PreToolUse" else "agent.tool.completed"
            )
        if hook == "PostToolUseFailure":
            data["status"] = "failed"
    # Kimi tool hooks have tool_call_id, not Codex's tool_use_id/turn_id.
    # ID-less hooks use the existing raw canonicalization, so distinct payloads
    # remain distinct while an exact replay has the same derived effect.
    call_id = (
        _string(payload, "tool_call_id")
        if hook in {"PreToolUse", "PostToolUse", "PostToolUseFailure"}
        else ""
    )
    occurrence = call_id or raw_payload_hash(payload)
    event_id = f"kimi:{hook}:{session_id}:{occurrence}"
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


def _conversation_message(
    payload: dict[str, Any], content: str, *, subagent: bool
) -> dict[str, Any]:
    hook = _event_name(payload)
    name = _string(payload, "agent_name")
    return {
        "message_role": "assistant" if subagent else "user",
        "participant": {
            "id": (f"subagent:{name}" if name else "subagent")
            if subagent
            else "operator",
            "type": "subagent" if subagent else "human",
            "role": "subagent" if subagent else "operator",
        },
        "session_id": _session_id(payload),
        "turn_id": _string(payload, "turn_id") or None,
        "content": content,
        "content_source": {
            "kind": "kimi_hook",
            "provider": "kimi",
            "adapter": "kimi-hooks",
            "native_event_type": hook,
            "content_provenance": "provider_payload",
        },
        "delivery": {
            "state": "complete",
            "sequence": 1 if subagent else 0,
            "final": True,
        },
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
    content = ""
    if hook == "UserPromptSubmit":
        content = _text(payload.get("prompt"))
    elif hook == "SubagentStop":
        content = _text(payload.get("response"))
    if content.strip() and envelope["source_session_id"]:
        envelope["derived_conversation_messages"] = [
            _conversation_message(payload, content, subagent=hook == "SubagentStop")
        ]
    return envelope


def _delivery_result(body: Any, transport: str) -> dict[str, Any]:
    """Keep admission failures terminal; transport success is not acceptance."""
    if not isinstance(body, dict):
        raise ValueError("runtime hook response is not an object")
    routing = body.get("routing_status")
    if routing == "ignored":
        return {**body, "status": "ignored", "transport": transport}
    if routing in {"denied", "quarantined"} or body.get("accepted") is False:
        return {**body, "status": "denied", "transport": transport}
    if (
        routing not in {"routed", "raw_accepted", "duplicate_raw"}
        or body.get("accepted") is not True
    ):
        raise ValueError("runtime hook response has no valid ingress receipt")
    return {**body, "status": "delivered", "transport": transport}


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
    except (OSError, SystemExit):
        pass
    else:
        # A running Runtime's HTTP rejection is terminal even when its CLI
        # wrapper returns nonzero. Only unavailable transport permits fallback.
        try:
            body = json.loads(output.getvalue())
            if exit_code != 0:
                return {
                    **(body if isinstance(body, dict) else {}),
                    "status": "denied",
                    "transport": "runtime",
                    "reason": "runtime_request_rejected",
                }
            return _delivery_result(body, "runtime")
        except ValueError:
            return {
                "status": "denied",
                "transport": "runtime",
                "reason": "runtime_invalid_receipt",
            }

    with contextlib.redirect_stdout(io.StringIO()):
        result = host.ingest_event(envelope, None, core)
    return _delivery_result(result, "ledger-fallback")


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
        logger.log(
            "warning" if result.get("status") == "denied" else "debug",
            "hook.result",
            {
                "status": result.get("status"),
                "transport": result.get("transport"),
                "reason": result.get("reason"),
                "normalized_event_count": len(result.get("normalized_event_ids") or []),
                "diagnostics": result.get("diagnostics"),
            },
            component="hooks",
            code="hook.result",
        )
    except (Exception, SystemExit) as exc:
        if hook in {"Stop", "SubagentStop"}:
            print("{}")
        logger.log(
            "error",
            "hook.ignored",
            {"exception": exc},
            component="hooks",
            code="hook.ignored",
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
