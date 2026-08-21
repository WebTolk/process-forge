"""Small read-only stdio MCP facade over existing PF Runtime/Core readers."""

from __future__ import annotations

import argparse
import copy
import importlib.util
import json
import os
import sys
from pathlib import Path
from typing import Any

_RUNTIME_BOOTSTRAP: Any | None = None

TOOLS = {
    "pf.project_state": "Read the current routed ProcessForge project state.",
    "pf.project_initialization.status": "Read bounded project initialization status for the Ledger-bound project.",
    "pf.project_initialization.initialize": "With apply: true only, initialize deterministic PF project state for the Ledger-bound project.",
    "pf.project_initialization.repair": "With apply: true only, repair deterministic PF snapshot state for the Ledger-bound project.",
    "pf.work_state": "Read current ProcessForge work state.",
    "pf.resolve": "Resolve a ProcessForge project or selected knowledge resource.",
    "pf.search": "Search only fresh snapshot-authorized local resources before using broader search.",
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
            raise session_read.SessionReadError("session_project_mismatch")
    if name == "pf.project_state":
        return host.project_state_payload(workplace, core, session=supplied_session)
    if name == "pf.project_initialization.status":
        from processforge_core import project_initialization

        return project_initialization.status(bound_project, core, workplace=str(workplace))
    if name in {"pf.project_initialization.initialize", "pf.project_initialization.repair"}:
        from processforge_core import project_initialization

        if arguments.get("apply") is not True:
            raise session_read.SessionReadError("apply_required")
        allowed = {
            "pf.project_initialization.initialize": {"session_id", "project_root", "apply", "answers", "project_type", "coordination_mode", "platforms", "specializations", "process", "force", "allow_missing_workplace"},
            "pf.project_initialization.repair": {"session_id", "project_root", "apply", "repair_action", "reason"},
        }
        if set(arguments) - allowed[name]:
            raise session_read.SessionReadError("invalid_arguments")
        request = {key: value for key, value in arguments.items() if key in allowed[name]}
        request["project_root"] = str(bound_project)
        request["workplace"] = str(workplace)
        request["command"] = f"mcp:{name}"
        try:
            if name.endswith(".initialize"):
                return project_initialization.initialize_project(request, core)
            return project_initialization.repair_project(request, core)
        except project_initialization.ProjectInitializationError as exc:
            raise session_read.SessionReadError(exc.code) from exc
    if name == "pf.work_state":
        return host.work_state_payload(workplace, core, session=supplied_session)
    if name == "pf.resolve":
        return host.resolve_payload(workplace, core, session=supplied_session, resource_id=str(arguments.get("resource_id") or "") or None)
    if name == "pf.search":
        from processforge_core.local_resource_search import LocalSearchError, search

        context = core.project_context_check_result(bound_project, explicit_workplace=str(workplace))
        if str(context.get("status") or "") not in {"fresh", "fresh_with_updates"}:
            raise LocalSearchError("snapshot_not_fresh")
        snapshot_path, _snapshot_md = core.project_context_snapshot_paths(bound_project)
        snapshot = core.load_yaml_document(snapshot_path)
        runtime_snapshot = copy.deepcopy(snapshot)
        resources = runtime_snapshot.get("local_search_resources") if isinstance(runtime_snapshot.get("local_search_resources"), list) else []
        for resource in resources:
            if not isinstance(resource, dict) or not isinstance(resource.get("path_ref"), dict):
                continue
            resolution = core.resolve_workspace_path_ref(bound_project, resource["path_ref"], workplace_manifest=workplace / "workplace.yaml")
            if resolution.get("status") == "resolved" and resolution.get("path"):
                # This physical root exists only in the request-local copy.
                # It is never persisted in the public snapshot or returned.
                resource["content_roots"] = [str(resolution["path"])]
        try:
            payload = search(bound_project, runtime_snapshot, query=arguments.get("query"), limit=arguments.get("limit"), limitstart=arguments.get("limitstart"), offset=arguments.get("offset"))
        except LocalSearchError as exc:
            raise session_read.SessionReadError(exc.code) from exc
        by_id = {str(item.get("id") or item.get("resource_id") or ""): item for item in resources if isinstance(item, dict)}
        for match in payload.get("results", []):
            if not isinstance(match, dict):
                continue
            resource = by_id.get(str(match.get("resource_id") or ""))
            roots = resource.get("content_roots") if isinstance(resource, dict) and isinstance(resource.get("content_roots"), list) else []
            for raw_root in roots:
                root = Path(str(raw_root)).resolve()
                candidate = (root / str(match.get("canonical_path") or "")).resolve() if root.is_dir() else root
                try:
                    candidate.relative_to(root if root.is_dir() else candidate)
                except ValueError:
                    continue
                if candidate.is_file():
                    match["local_path"] = str(candidate)
                    match["navigation"] = "private_runtime_authorized"
                    break
        return payload
    if name == "pf.workplace_state":
        return host.workplace_state_payload(workplace, core)
    raise session_read.SessionReadError("unknown_tool")


def tool_schema(name: str) -> dict[str, Any]:
    properties: dict[str, Any] = {"session_id": {"type": "string"}, "project_root": {"type": "string"}}
    if name == "pf.resolve":
        properties["resource_id"] = {"type": "string"}
    if name == "pf.search":
        properties.update({"query": {"type": "string", "minLength": 1}, "limit": {"type": "integer", "minimum": 1, "maximum": 100}, "limitstart": {"type": "integer", "minimum": 0}, "offset": {"type": "integer", "minimum": 0}})
    if name == "pf.project_initialization.initialize":
        properties.update({"apply": {"type": "boolean"}, "answers": {"type": "object"}, "project_type": {"type": "string"}, "coordination_mode": {"type": "string", "enum": ["inherit", "simple", "organized"]}, "platforms": {"type": "array", "items": {"type": "string"}}, "specializations": {"type": "array", "items": {"type": "string"}}, "process": {"type": "string"}, "force": {"type": "boolean"}, "allow_missing_workplace": {"type": "boolean"}})
    if name == "pf.project_initialization.repair":
        properties.update({"apply": {"type": "boolean"}, "repair_action": {"type": "string", "enum": ["refresh_context", "restore_deterministic_artifacts"]}, "reason": {"type": "string"}})
    if name in {"pf.session_chat", "pf.session_activity"}:
        properties["limit"] = {"type": "integer", "minimum": 1, "maximum": 100}
    if name == "pf.session_chat":
        properties.update({"before": {"type": "string"}, "cursor": {"type": "string"}, "roles": {"type": "array", "items": {"type": "string", "enum": ["user", "assistant", "system"]}}})
    return {"type": "object", "properties": properties}


def safe_tool_error(exc: Exception) -> str:
    from pf_runtime import session_read

    code = getattr(exc, "code", "read_failed")
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
        except (Exception, SystemExit) as exc:
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
