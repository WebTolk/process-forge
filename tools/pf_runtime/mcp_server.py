"""Small read-only stdio MCP facade over existing PF Runtime/Core readers."""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import sys
from pathlib import Path
from typing import Any

_RUNTIME_BOOTSTRAP: Any | None = None

TOOLS = {
    "pf.project_state": "Read the current routed ProcessForge project state.",
    "pf.work_state": "Read current ProcessForge work state.",
    "pf.resolve": "Resolve a ProcessForge project or selected knowledge resource.",
    "pf.workplace_state": "Read derived workplace ledger state.",
    "pf.session_context": "Read a bounded current-context projection for the Ledger-bound session.",
    "pf.session_chat": "Read paginated private transcript messages for the Ledger-bound session.",
    "pf.session_activity": "Read bounded normalized activity facts for the Ledger-bound session.",
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


def tool_result(name: str, arguments: dict[str, Any], workplace: Path, session_id: str, runtime: Any) -> dict[str, Any]:
    host = runtime.host
    core = runtime.core
    from pf_runtime import session_read

    configured_session = str(session_id or "")
    requested_session = str(arguments.get("session_id") or "")
    if configured_session and requested_session and requested_session != configured_session:
        raise session_read.SessionReadError("session_mismatch")
    supplied_session = configured_session or requested_session
    project_root = arguments.get("project_root")
    if name == "pf.session_context":
        return session_read.session_context_payload(workplace, core, session_id=supplied_session, project_root_ref=project_root)
    if name == "pf.session_chat":
        return session_read.session_chat_payload(workplace, core, session_id=supplied_session, project_root_ref=project_root, limit=arguments.get("limit"), before=arguments.get("before"), cursor=arguments.get("cursor"), roles=arguments.get("roles"))
    if name == "pf.session_activity":
        return session_read.session_activity_payload(workplace, core, session_id=supplied_session, project_root_ref=project_root, limit=arguments.get("limit"))
    if not supplied_session:
        raise session_read.SessionReadError("missing_session")
    # A stdio MCP server has no HTTP handler to enforce this for us.  Bind the
    # supplied session to Ledger first and reject every conflicting project.
    bound_project = host.project_for_session(argparse.Namespace(session=supplied_session, project_root=None), workplace, core)
    if project_root:
        requested_project = host.resolve_project(str(project_root), core)
        if core.project_id(bound_project) != core.project_id(requested_project):
            raise PermissionError("session is not authorized for requested project_root")
    if name == "pf.project_state":
        return host.project_state_payload(workplace, core, session=supplied_session)
    if name == "pf.work_state":
        return host.work_state_payload(workplace, core, session=supplied_session)
    if name == "pf.resolve":
        return host.resolve_payload(workplace, core, session=supplied_session, resource_id=str(arguments.get("resource_id") or "") or None)
    if name == "pf.workplace_state":
        return host.workplace_state_payload(workplace, core)
    raise session_read.SessionReadError("unknown_tool")


def tool_schema(name: str) -> dict[str, Any]:
    properties: dict[str, Any] = {"session_id": {"type": "string"}, "project_root": {"type": "string"}}
    if name == "pf.resolve":
        properties["resource_id"] = {"type": "string"}
    if name in {"pf.session_chat", "pf.session_activity"}:
        properties["limit"] = {"type": "integer", "minimum": 1, "maximum": 100}
    if name == "pf.session_chat":
        properties.update({"before": {"type": "string"}, "cursor": {"type": "string"}, "roles": {"type": "array", "items": {"type": "string", "enum": ["user", "assistant", "system"]}}})
    return {"type": "object", "properties": properties}


def safe_tool_error(exc: Exception) -> str:
    from pf_runtime import session_read

    code = exc.code if isinstance(exc, session_read.SessionReadError) else "read_failed"
    return json.dumps({"error": {"code": code}}, ensure_ascii=False, sort_keys=True)


def respond(request: dict[str, Any], workplace: Path, session_id: str, runtime: Any) -> dict[str, Any] | None:
    core = runtime.core
    method = str(request.get("method") or "")
    request_id = request.get("id")
    if method == "notifications/initialized":
        return None
    if method == "initialize":
        return {"jsonrpc": "2.0", "id": request_id, "result": {"protocolVersion": "2024-11-05", "serverInfo": {"name": "processforge", "version": str(getattr(core, "PROCESSFORGE_VERSION", "1"))}, "capabilities": {"tools": {}}}}
    if method == "tools/list":
        tools = [{"name": name, "description": description, "inputSchema": tool_schema(name)} for name, description in TOOLS.items()]
        return {"jsonrpc": "2.0", "id": request_id, "result": {"tools": tools}}
    if method == "tools/call":
        params = request.get("params") if isinstance(request.get("params"), dict) else {}
        try:
            result = tool_result(str(params.get("name") or ""), params.get("arguments") if isinstance(params.get("arguments"), dict) else {}, workplace, session_id, runtime)
            return {"jsonrpc": "2.0", "id": request_id, "result": {"content": [{"type": "text", "text": json.dumps(result, ensure_ascii=False, sort_keys=True)}]}}
        except Exception as exc:
            return {"jsonrpc": "2.0", "id": request_id, "result": {"content": [{"type": "text", "text": safe_tool_error(exc)}], "isError": True}}
    return {"jsonrpc": "2.0", "id": request_id, "error": {"code": -32601, "message": "method not found"}}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workplace", required=True)
    parser.add_argument("--session", default=os.environ.get("PF_MCP_SESSION_ID", ""))
    args = parser.parse_args()
    runtime = runtime_bootstrap()
    core = runtime.core
    workplace = core.resolve_workplace_root(args.workplace)
    for line in sys.stdin:
        if not line.strip():
            continue
        try:
            response = respond(json.loads(line), workplace, args.session, runtime)
            if response is not None:
                print(json.dumps(response, ensure_ascii=False), flush=True)
        except Exception:
            print(json.dumps({"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": "invalid request"}}, ensure_ascii=False), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
