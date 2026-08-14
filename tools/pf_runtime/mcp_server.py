"""Small read-only stdio MCP facade over existing PF Runtime/Core readers."""

from __future__ import annotations

import argparse
import importlib
import json
import os
import sys
from pathlib import Path
from typing import Any

TOOLS_ROOT = str(Path(__file__).resolve().parents[1])
if TOOLS_ROOT not in sys.path:
    sys.path.insert(0, TOOLS_ROOT)


TOOLS = {
    "pf.project_state": "Read the current routed ProcessForge project state.",
    "pf.work_state": "Read current ProcessForge work state.",
    "pf.resolve": "Resolve a ProcessForge project or selected knowledge resource.",
    "pf.workplace_state": "Read derived workplace ledger state.",
}


def core_module() -> Any:
    return importlib.import_module("processforge")


def tool_result(name: str, arguments: dict[str, Any], workplace: Path, session_id: str, core: Any) -> dict[str, Any]:
    from pf_runtime import host

    supplied_session = str(arguments.get("session_id") or session_id or "")
    if not supplied_session:
        raise ValueError("PF_MCP_SESSION_ID or session_id is required")
    project_root = arguments.get("project_root")
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
    raise ValueError(f"unknown tool: {name}")


def respond(request: dict[str, Any], workplace: Path, session_id: str, core: Any) -> dict[str, Any] | None:
    method = str(request.get("method") or "")
    request_id = request.get("id")
    if method == "notifications/initialized":
        return None
    if method == "initialize":
        return {"jsonrpc": "2.0", "id": request_id, "result": {"protocolVersion": "2024-11-05", "serverInfo": {"name": "processforge", "version": str(getattr(core, "PROCESSFORGE_VERSION", "1"))}, "capabilities": {"tools": {}}}}
    if method == "tools/list":
        tools = [{"name": name, "description": description, "inputSchema": {"type": "object", "properties": {"session_id": {"type": "string"}, "project_root": {"type": "string"}, "resource_id": {"type": "string"}}}} for name, description in TOOLS.items()]
        return {"jsonrpc": "2.0", "id": request_id, "result": {"tools": tools}}
    if method == "tools/call":
        params = request.get("params") if isinstance(request.get("params"), dict) else {}
        try:
            result = tool_result(str(params.get("name") or ""), params.get("arguments") if isinstance(params.get("arguments"), dict) else {}, workplace, session_id, core)
            return {"jsonrpc": "2.0", "id": request_id, "result": {"content": [{"type": "text", "text": json.dumps(result, ensure_ascii=False, sort_keys=True)}]}}
        except Exception as exc:
            return {"jsonrpc": "2.0", "id": request_id, "result": {"content": [{"type": "text", "text": str(exc)}], "isError": True}}
    return {"jsonrpc": "2.0", "id": request_id, "error": {"code": -32601, "message": "method not found"}}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workplace", required=True)
    parser.add_argument("--session", default=os.environ.get("PF_MCP_SESSION_ID", ""))
    args = parser.parse_args()
    core = core_module()
    workplace = core.resolve_workplace_root(args.workplace)
    for line in sys.stdin:
        if not line.strip():
            continue
        try:
            response = respond(json.loads(line), workplace, args.session, core)
            if response is not None:
                print(json.dumps(response, ensure_ascii=False), flush=True)
        except Exception as exc:
            print(json.dumps({"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": str(exc)}}, ensure_ascii=False), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
