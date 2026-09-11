"""Small read-oriented stdio MCP facade over PF Runtime/Core services."""

from __future__ import annotations

import argparse
import importlib.util
import json
import math
import os
import sys
from pathlib import Path
from typing import Any

_RUNTIME_BOOTSTRAP: Any | None = None

TOOLS = {
    "pf.context": "Read Garage context for a ProcessForge project without requiring a Ledger session.",
    "pf.project_state": "Read the current routed ProcessForge project state.",
    "pf.project_initialization.status": "Read bounded project initialization status for a ProcessForge project.",
    "pf.project_initialization.initialize": "With apply: true only, initialize deterministic PF project state for the Ledger-bound project.",
    "pf.project_initialization.repair": "With apply: true only, repair deterministic PF snapshot state for the Ledger-bound project.",
    "pf.work_state": "Compatibility alias for the current declarative work state.",
    "pf.work.state": "Read the current declarative ProcessForge work state.",
    "pf.work.start": "Start or continue governed ProcessForge work from a high-level objective.",
    "pf.work.transition": "Advance governed work using a declared outcome and evidence.",
    "pf.resolve": "Resolve a ProcessForge project or selected knowledge resource.",
    "pf.search": "Search only fresh snapshot-authorized local resources before using broader search.",
    "pf.workplace_state": "Read derived workplace ledger state.",
    "pf.session_context": "Read a bounded current-context projection for the Ledger-bound session.",
    "pf.session_chat": "Read paginated private transcript messages for the Ledger-bound session.",
    "pf.session_activity": "Read bounded normalized activity facts for the Ledger-bound session.",
}

MUTATING_TOOLS = {
    "pf.project_initialization.initialize",
    "pf.project_initialization.repair",
    "pf.work.start",
    "pf.work.transition",
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
    from processforge_core.local_resource_search import LocalSearchError
    from processforge_core.garage import GovernedWorkBootstrapService, ProjectContextService, ResourceResolveService, ResourceSearchService
    from processforge_core.process_execution import ProcessExecutionService

    configured_session = str(session_id or "")
    requested_session = str(arguments.get("session_id") or "")
    if configured_session and requested_session and requested_session != configured_session:
        raise session_read.SessionReadError("session_mismatch")
    supplied_session = configured_session or requested_session
    project_root = arguments.get("project_root")

    def resolve_garage_project() -> Path:
        if project_root:
            candidate = host.resolve_project(str(project_root), core)
            if supplied_session:
                bound = host.project_for_session(argparse.Namespace(session=supplied_session, project_root=None), workplace, core)
                if core.project_id(bound) != core.project_id(candidate):
                    raise session_read.SessionReadError("session_project_mismatch")
            return candidate
        if supplied_session:
            return host.project_for_session(argparse.Namespace(session=supplied_session, project_root=None), workplace, core)
        raise session_read.SessionReadError("missing_project_root")

    if name == "pf.session_context":
        return session_read.session_context_payload(workplace, core, session_id=supplied_session, project_root_ref=project_root)
    if name == "pf.session_chat":
        return session_read.session_chat_payload(workplace, core, session_id=supplied_session, project_root_ref=project_root, limit=arguments.get("limit"), before=arguments.get("before"), cursor=arguments.get("cursor"), roles=arguments.get("roles"))
    if name == "pf.session_activity":
        return session_read.session_activity_payload(workplace, core, session_id=supplied_session, project_root_ref=project_root, limit=arguments.get("limit"))
    if name == "pf.context":
        bound_project = resolve_garage_project()
        service = ProjectContextService(bound_project, workplace, core)
        context = service.context(session_id=supplied_session)
        snapshot = service.snapshot()
        knowledge = snapshot.get("knowledge_resources") if isinstance(snapshot.get("knowledge_resources"), dict) else {}
        selected = knowledge.get("selected") if isinstance(knowledge.get("selected"), list) else []
        active_work = context.get("work", {}).get("active_work", []) if isinstance(context.get("work"), dict) else []
        current_work = ProcessExecutionService(bound_project, workplace, core).state(session_id=supplied_session)
        # Keep the MCP bootstrap response bounded. Full assignment objectives
        # can be large and are already available through the governed capsule.
        payload = {
            "schema_version": 1,
            "kind": "pf.context",
            "mode": context.get("mode"),
            "project": context.get("project", {}),
            "context": context.get("context", {}),
            "process": context.get("process", {}),
            "resources": {
                **(context.get("resources", {}) if isinstance(context.get("resources"), dict) else {}),
                "authorized_knowledge_ids": [str(item.get("id")) for item in selected if isinstance(item, dict) and item.get("id")],
            },
            "work": {
                "governed": bool(context.get("work", {}).get("governed")) if isinstance(context.get("work"), dict) else False,
                "active_runs": context.get("work", {}).get("active_runs", []) if isinstance(context.get("work"), dict) else [],
                "active_work": [
                    {key: item.get(key) for key in ("run_id", "assignment_id", "run_status", "status", "state", "stage", "process")}
                    for item in active_work
                    if isinstance(item, dict)
                ],
                "recommendation": context.get("work", {}).get("recommendation") if isinstance(context.get("work"), dict) else None,
                "current": current_work if current_work.get("action") != "start_recommended" else {"action": "start_recommended"},
            },
            "session": context.get("session", {}),
            "derived_reports": context.get("derived_reports", {}),
            "diagnostics": context.get("diagnostics", []),
        }
        if isinstance(context.get("continuation"), dict):
            payload["continuation"] = context["continuation"]
        return payload
    if name == "pf.project_state":
        bound_project = resolve_garage_project()
        return host.project_state_payload(workplace, core, session=supplied_session, project_root_ref=str(bound_project))
    if name == "pf.project_initialization.status":
        from processforge_core import project_initialization

        bound_project = resolve_garage_project()
        return project_initialization.status(bound_project, core, workplace=str(workplace))
    if name == "pf.work_state":
        bound_project = resolve_garage_project()
        context = ProjectContextService(bound_project, workplace, core).context(session_id=supplied_session)
        return {"project": context["project"], "work": context["work"], "context": context["context"], "session": context.get("session", {})}
    if name == "pf.work.state":
        bound_project = resolve_garage_project()
        return ProcessExecutionService(bound_project, workplace, core).state(session_id=supplied_session)
    if name == "pf.work.start":
        if set(arguments) - {"session_id", "project_root", "objective", "process_id"}:
            raise session_read.SessionReadError("invalid_arguments")
        bound_project = resolve_garage_project()
        return GovernedWorkBootstrapService(bound_project, workplace, core).start(objective=str(arguments.get("objective") or ""), process_id=str(arguments.get("process_id") or ""), session_id=supplied_session)
    if name == "pf.work.transition":
        bound_project = resolve_garage_project()
        return ProcessExecutionService(bound_project, workplace, core).transition(
            outcome=str(arguments.get("outcome") or ""),
            evidence=arguments.get("evidence"),
            notes=str(arguments.get("notes") or ""),
            session_id=supplied_session,
        )
    if name == "pf.resolve":
        bound_project = resolve_garage_project()
        context = core.project_context_check_result(bound_project, explicit_workplace=str(workplace))
        if str(context.get("status") or "") not in {"fresh", "fresh_with_updates"}:
            raise session_read.SessionReadError("snapshot_not_fresh")
        return ResourceResolveService(bound_project, workplace, core).resolve(resource_id=str(arguments.get("resource_id") or "") or None)
    if name == "pf.search":
        bound_project = resolve_garage_project()
        try:
            return ResourceSearchService(bound_project, workplace, core).search(query=arguments.get("query"), limit=arguments.get("limit"), limitstart=arguments.get("limitstart"), offset=arguments.get("offset"))
        except LocalSearchError as exc:
            raise session_read.SessionReadError(exc.code) from exc
    if not supplied_session:
        raise session_read.SessionReadError("missing_session")
    # A stdio MCP server has no HTTP handler to enforce this for us.  Bind the
    # supplied session to Ledger first and reject every conflicting project.
    bound_project = host.project_for_session(argparse.Namespace(session=supplied_session, project_root=None), workplace, core)
    if project_root:
        requested_project = host.resolve_project(str(project_root), core)
        if core.project_id(bound_project) != core.project_id(requested_project):
            raise session_read.SessionReadError("session_project_mismatch")
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
    if name == "pf.workplace_state":
        return host.workplace_state_payload(workplace, core)
    raise session_read.SessionReadError("unknown_tool")


def tool_schema(name: str) -> dict[str, Any]:
    properties: dict[str, Any] = {"session_id": {"type": "string"}, "project_root": {"type": "string"}}
    required: list[str] = []
    if name == "pf.resolve":
        properties["resource_id"] = {"type": "string"}
    if name == "pf.search":
        properties.update({"query": {"type": "string", "minLength": 1}, "limit": {"type": "integer", "minimum": 1, "maximum": 100}, "limitstart": {"type": "integer", "minimum": 0}, "offset": {"type": "integer", "minimum": 0}})
    if name == "pf.work.start":
        properties.update({"objective": {"type": "string", "minLength": 1}})
        properties["process_id"] = {"type": "string", "minLength": 1}
        required.append("objective")
    if name == "pf.work.transition":
        properties.update(
            {
                "outcome": {"type": "string", "minLength": 1},
                "evidence": {
                    "type": "array",
                    "items": {"oneOf": [{"type": "string"}, {"type": "object", "additionalProperties": True}]},
                },
                "notes": {"type": "string"},
            }
        )
        required.append("outcome")
    if name == "pf.project_initialization.initialize":
        properties.update({"apply": {"type": "boolean"}, "answers": {"type": "object"}, "project_type": {"type": "string"}, "coordination_mode": {"type": "string", "enum": ["inherit", "simple", "organized"]}, "platforms": {"type": "array", "items": {"type": "string"}}, "specializations": {"type": "array", "items": {"type": "string"}}, "process": {"type": "string"}, "force": {"type": "boolean"}, "allow_missing_workplace": {"type": "boolean"}})
    if name == "pf.project_initialization.repair":
        properties.update({"apply": {"type": "boolean"}, "repair_action": {"type": "string", "enum": ["refresh_context", "restore_deterministic_artifacts", "install_codex_hooks"]}, "reason": {"type": "string"}})
    if name in {"pf.session_chat", "pf.session_activity"}:
        properties["limit"] = {"type": "integer", "minimum": 1, "maximum": 100}
    if name == "pf.session_chat":
        properties.update({"before": {"type": "string"}, "cursor": {"type": "string"}, "roles": {"type": "array", "items": {"type": "string", "enum": ["user", "assistant", "system"]}}})
    schema: dict[str, Any] = {"type": "object", "properties": properties, "additionalProperties": False}
    if required:
        schema["required"] = required
    return schema


def tool_annotations(name: str) -> dict[str, bool]:
    mutating = name in MUTATING_TOOLS
    return {
        "readOnlyHint": not mutating,
        "destructiveHint": False,
        "idempotentHint": not mutating,
        "openWorldHint": False,
    }


def safe_tool_error(exc: Exception) -> str:
    from pf_runtime import session_read

    code = getattr(exc, "code", "read_failed")
    error: dict[str, Any] = {"code": code}
    if code == "missing_session":
        error["remediation"] = {
            "kind": "ledger_session_required",
            "summary": "This Forge-only MCP tool requires a real Ledger-bound host session id.",
            "checks": [
                "Use pf.context, pf.project_state, pf.work_state, pf.resolve, pf.search, or pf.work.start when the operation can stay in Garage mode.",
                "Ask the operator to verify the configured host session integration and Agent Ledger route when a Forge-only view is required.",
                "After the operator resolves host integration, retry from a fresh host session.",
            ],
            "repair_actions": [],
            "operator_action": "verify_host_session_integration",
            "manual_fallback": "Use session-start only for controlled local diagnostics; do not invent production session ids.",
        }
    elif code in {"unknown_session", "session_not_routed", "session_project_mismatch"}:
        error["remediation"] = {
            "kind": "ledger_session_binding_invalid",
            "summary": "The supplied session id is not bound to the requested project in Ledger.",
            "checks": [
                "Use the current session id recorded by Codex hook ingress.",
                "Verify the session project root matches the MCP request project_root.",
            ],
        }
    elif code == "missing_project_root":
        error["remediation"] = {
            "kind": "project_root_required",
            "summary": "Garage read-only tools can run without a Ledger session, but need project_root when no session is supplied.",
            "checks": ["Call pf.context, pf.search, pf.resolve, or pf.work.start with project_root set to a valid ProcessForge project."],
        }
    return json.dumps({"error": error}, ensure_ascii=False, sort_keys=True)


def schema_accepts(value: Any, schema: dict[str, Any]) -> bool:
    """Validate the bounded JSON Schema vocabulary used by tool_schema()."""
    if "anyOf" in schema and not any(schema_accepts(value, item) for item in schema["anyOf"]):
        return False
    if "oneOf" in schema and sum(schema_accepts(value, item) for item in schema["oneOf"]) != 1:
        return False
    types = {
        "object": isinstance(value, dict), "array": isinstance(value, list),
        "string": isinstance(value, str), "boolean": isinstance(value, bool),
        "integer": isinstance(value, int) and not isinstance(value, bool),
    }
    if "type" in schema and not types.get(schema["type"], False):
        return False
    if "enum" in schema and value not in schema["enum"]:
        return False
    if isinstance(value, str) and len(value) < schema.get("minLength", 0):
        return False
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if value < schema.get("minimum", value) or value > schema.get("maximum", value):
            return False
    if isinstance(value, dict):
        properties = schema.get("properties", {})
        if any(key not in value for key in schema.get("required", [])):
            return False
        if schema.get("additionalProperties") is False and set(value) - set(properties):
            return False
        if any(key in value and not schema_accepts(value[key], item) for key, item in properties.items()):
            return False
    if isinstance(value, list) and "items" in schema:
        return all(schema_accepts(item, schema["items"]) for item in value)
    return True


def rpc_error(request_id: Any, code: int, message: str) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": request_id, "error": {"code": code, "message": message}}


def respond(request: Any, workplace: Path, session_id: str, runtime: Any) -> dict[str, Any] | None:
    request_id = request.get("id") if isinstance(request, dict) else None
    valid_id = request_id is None or isinstance(request_id, str) or (type(request_id) in {int, float} and (not isinstance(request_id, float) or math.isfinite(request_id)))
    if not isinstance(request, dict) or request.get("jsonrpc") != "2.0" or not isinstance(request.get("method"), str) or not valid_id:
        return rpc_error(request_id if valid_id else None, -32600, "invalid request")
    notification = "id" not in request
    method = request["method"]
    params = request.get("params", {})
    params_valid = isinstance(params, dict)
    if params_valid and method == "tools/call":
        name = params.get("name")
        params_valid = isinstance(name, str) and name in TOOLS and schema_accepts(params, {
            "type": "object", "required": ["name"], "additionalProperties": False,
            "properties": {"name": {"type": "string"}, "arguments": {"type": "object"}, "_meta": {"type": "object"}},
        })
        if params_valid:
            params_valid = schema_accepts(params.get("arguments", {}), tool_schema(name))
    elif params_valid and method in {"initialize", "tools/list"}:
        params_valid = schema_accepts(params, {"type": "object", "properties": {
            "_meta": {"type": "object"}, "cursor": {"type": "string"},
            "protocolVersion": {"type": "string"}, "capabilities": {"type": "object"},
            "clientInfo": {"type": "object", "properties": {"name": {"type": "string"}, "version": {"type": "string"}}},
        }})
    if not params_valid:
        return None if notification else rpc_error(request_id, -32602, "invalid params")
    response = respond_valid(request, workplace, session_id, runtime)
    return None if notification else response


def respond_valid(request: dict[str, Any], workplace: Path, session_id: str, runtime: Any) -> dict[str, Any] | None:
    core = runtime.core
    method = str(request.get("method") or "")
    request_id = request.get("id")
    if method == "notifications/initialized":
        return {"jsonrpc": "2.0", "id": request_id, "result": {}}
    if method == "initialize":
        return {"jsonrpc": "2.0", "id": request_id, "result": {"protocolVersion": "2024-11-05", "serverInfo": {"name": "processforge", "version": str(getattr(core, "PROCESSFORGE_VERSION", "1"))}, "capabilities": {"tools": {}}}}
    if method == "tools/list":
        tools = [{"name": name, "description": description, "inputSchema": tool_schema(name), "annotations": tool_annotations(name)} for name, description in TOOLS.items()]
        return {"jsonrpc": "2.0", "id": request_id, "result": {"tools": tools}}
    if method == "tools/call":
        params = request.get("params") if isinstance(request.get("params"), dict) else {}
        try:
            result = tool_result(str(params.get("name") or ""), params.get("arguments") if isinstance(params.get("arguments"), dict) else {}, workplace, session_id, runtime)
            return {"jsonrpc": "2.0", "id": request_id, "result": {"content": [{"type": "text", "text": json.dumps(result, ensure_ascii=False, sort_keys=True)}]}}
        except (Exception, SystemExit) as exc:
            return {"jsonrpc": "2.0", "id": request_id, "result": {"content": [{"type": "text", "text": safe_tool_error(exc)}], "isError": True}}
    return {"jsonrpc": "2.0", "id": request_id, "error": {"code": -32601, "message": "method not found"}}


def reject_json_constant(value: str) -> Any:
    raise ValueError(f"invalid JSON constant: {value}")


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
            request = json.loads(line, parse_constant=reject_json_constant)
        except (json.JSONDecodeError, ValueError):
            print(json.dumps(rpc_error(None, -32700, "parse error")), flush=True)
            continue
        try:
            response = respond(request, workplace, args.session, runtime)
        except Exception:
            response = rpc_error(request.get("id"), -32603, "internal error") if isinstance(request, dict) and "id" in request else None
        if response is not None:
            print(json.dumps(response, ensure_ascii=False), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
