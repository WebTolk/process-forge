"""Typed MCP adapters for discovery and a bounded set of existing native actions."""

from __future__ import annotations

import argparse
from collections.abc import Callable, Mapping
from contextlib import redirect_stderr, redirect_stdout
from copy import deepcopy
from dataclasses import dataclass
import io
from pathlib import Path
from typing import Any

import yaml


TOOL_DESCRIPTIONS = {
    "pf.actions.list": "List supported CLI/MCP actions with bounded filtering and truthful native-validation requirements; discovery grants no permissions.",
    "pf.actions.describe": "Describe one exact supported action, its actual arguments/schema, effects and preconditions; never execute it.",
    "pf.runtime_driver.list": "List registered native runtime driver IDs and status for this project/workplace; never launch a worker.",
    "pf.runtime_driver.describe": "Read safe metadata for one registered driver ID; no executable override, environment values or arbitrary manifest paths.",
    "pf.worker.prepare": "With apply true, prepare the exact active Work using an explicitly selected registered driver; preserve native scope/input checks.",
    "pf.worker.start": "With apply true, start the exact active Work through its native registered driver and return immediately; no shell/executable override.",
    "pf.worker.status": "With apply true, observe the exact Work's native worker status; observation may reconcile runtime records and collect completed output.",
    "pf.worker.collect": "With apply true, collect the current native attempt for the exact active Work through existing report/hash validation.",
    "pf.session.heartbeat": "With apply true, renew only the already bound Ledger session; never register, impersonate or create a session.",
    "pf.chat.record": "With apply true, append an assistant message as the bound Ledger agent to its own PF session transcript; no external messaging.",
}

MUTATING_TOOL_NAMES = {
    "pf.worker.prepare", "pf.worker.start", "pf.worker.status", "pf.worker.collect",
    "pf.session.heartbeat", "pf.chat.record",
}

WORK_TOOL_NAMES = {name for name in TOOL_DESCRIPTIONS if name.startswith("pf.worker.")}
SESSION_TOOL_NAMES = {"pf.session.heartbeat", "pf.chat.record"}


class ActionToolError(ValueError):
    """A bounded adapter refusal, before a native action is invoked."""

    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


def action_tool_schema(name: str) -> dict[str, Any]:
    if name not in TOOL_DESCRIPTIONS:
        raise ActionToolError("unknown_tool")
    properties: dict[str, Any] = {
        "project_root": {"type": "string"}, "session_id": {"type": "string"},
    }
    required: list[str] = []
    if name == "pf.actions.list":
        properties.update({
            "query": {"type": "string", "maxLength": 256},
            "surface": {"type": "string", "enum": ["cli", "mcp"]},
            "limit": {"type": "integer", "minimum": 1, "maximum": 100},
            "offset": {"type": "integer", "minimum": 0},
        })
    if name == "pf.actions.describe":
        properties["action_id"] = {"type": "string", "minLength": 1, "maxLength": 256}
        required.append("action_id")
    if name.startswith("pf.actions.") or name in WORK_TOOL_NAMES:
        properties.update({key: {"type": "string", "minLength": 1} for key in ("run_id", "assignment_id", "context_id")})
    if name in WORK_TOOL_NAMES:
        required.extend(["run_id", "assignment_id", "context_id"])
    if name in {"pf.runtime_driver.describe", "pf.worker.prepare", "pf.worker.start"}:
        properties["driver"] = {"type": "string", "minLength": 1, "maxLength": 128}
        required.append("driver")
    if name in {"pf.worker.prepare", "pf.worker.start"}:
        properties.update({
            "model": {"type": "string", "minLength": 1, "maxLength": 256},
            "reasoning_effort": {"type": "string", "enum": ["minimal", "low", "medium", "high"]},
        })
    if name in MUTATING_TOOL_NAMES:
        properties["apply"] = {"type": "boolean"}
        required.append("apply")
    if name == "pf.chat.record":
        properties["content"] = {"type": "string", "minLength": 1, "maxLength": 32768}
        required.append("content")
    result: dict[str, Any] = {"type": "object", "properties": properties, "additionalProperties": False}
    if required:
        result["required"] = required
    return result


@dataclass(frozen=True)
class ActionToolDependencies:
    parser_factory: Callable[[], argparse.ArgumentParser]
    native_command: Callable[[list[str]], int]
    registered_driver_ref: Callable[[str], str]
    work_state: Callable[..., dict[str, Any]]
    session_record: Callable[[], dict[str, Any]]
    version: str
    identity: Callable[[], dict[str, Any]] | None = None


@dataclass(frozen=True)
class NativeResult:
    exit_code: int
    stdout: str
    stderr: str

    @property
    def output(self) -> str:
        return self.stdout + self.stderr


class NativeActionGateway:
    """Invoke an explicitly composed native handler without a shell or subprocess CLI."""

    def __init__(self, execute_command: Callable[[list[str]], int]):
        self._execute_command = execute_command

    def call(self, argv: list[str]) -> NativeResult:
        output, errors = io.StringIO(), io.StringIO()
        with redirect_stdout(output), redirect_stderr(errors):
            try:
                code = int(self._execute_command(list(argv)) or 0)
            except SystemExit as exc:
                code = exc.code if isinstance(exc.code, int) else 1
                if isinstance(exc.code, str):
                    errors.write(exc.code)
        return NativeResult(code, output.getvalue(), errors.getvalue())


class ActionToolService:
    """Adapt only the declared operations; native implementations retain authority."""

    def __init__(self, dependencies: ActionToolDependencies, project_root: Path, workplace: Path, session_id: str):
        self._dependencies = dependencies
        self._project = project_root
        self._workplace = workplace
        self._session_id = session_id
        self._native = NativeActionGateway(dependencies.native_command)

    def _work(self, arguments: Mapping[str, Any], *, execution: bool) -> dict[str, Any]:
        keys = ("run_id", "assignment_id", "context_id")
        if not all(isinstance(arguments.get(key), str) and arguments[key].strip() for key in keys):
            raise ActionToolError("work_selectors_required")
        state = self._dependencies.work_state(**{key: arguments[key] for key in keys})
        if (state.get("run", {}).get("id"), state.get("assignment", {}).get("id"), state.get("context", {}).get("id")) != tuple(arguments[key] for key in keys):
            raise ActionToolError("work_context_mismatch")
        if state.get("context", {}).get("validation", {}).get("status") != "valid":
            raise ActionToolError("work_context_invalid")
        if execution:
            if state.get("run", {}).get("status") in {"completed", "failed", "cancelled"} or state.get("assignment", {}).get("status") in {"done", "completed", "failed", "cancelled"}:
                raise ActionToolError("work_is_terminal")
            if state.get("execution_readiness", {}).get("status") != "ready" or state.get("blockers"):
                raise ActionToolError("work_not_ready")
        return state

    def _invoke(self, command: list[str], values: Mapping[str, Any], *, workplace: bool = False) -> NativeResult:
        argv = command + ["--project-root=" + str(self._project)]
        if workplace:
            argv.append("--workplace=" + str(self._workplace))
        for key, value in values.items():
            if value is True:
                argv.append("--" + key.replace("_", "-"))
            elif value is not None and value is not False:
                # Keep values beginning with '-' literal, including chat content.
                argv.append("--" + key.replace("_", "-") + "=" + str(value))
        return self._native.call(argv)

    @staticmethod
    def _failure(name: str, result: NativeResult) -> dict[str, Any]:
        return {"schema_version": 1, "kind": name, "status": "blocked", "reason": "native_operation_failed", "native_exit_code": result.exit_code,
                "native_diagnostic": result.output[-2000:]}

    def _drivers(self) -> tuple[NativeResult, list[dict[str, str]]]:
        result = self._invoke(["runtime-driver", "list"], {}, workplace=True)
        rows = []
        if result.exit_code == 0:
            for line in result.stdout.splitlines():
                values = line.split("\t")
                if len(values) >= 2:
                    rows.append({"id": values[0], "status": values[1]})
        return result, rows

    def execute(self, name: str, arguments: Mapping[str, Any]) -> dict[str, Any]:
        schema = action_tool_schema(name)
        from pf_runtime.mcp_server import schema_accepts

        if not schema_accepts(dict(arguments), schema):
            raise ActionToolError("invalid_arguments")
        if name in MUTATING_TOOL_NAMES and arguments.get("apply") is not True:
            raise ActionToolError("apply_required")
        if name.startswith("pf.actions."):
            selectors = [key in arguments for key in ("run_id", "assignment_id", "context_id")]
            if any(selectors) and not all(selectors):
                raise ActionToolError("work_selectors_required")
            state = self._work(arguments, execution=False) if all(selectors) else None
            from pf_runtime.action_catalog import catalog_payload

            catalogue_payload = catalog_payload(self._dependencies.parser_factory, operation=name.rsplit(".", 1)[1], version=self._dependencies.version,
                                   **{key: arguments[key] for key in ("action_id", "query", "surface", "limit", "offset") if key in arguments}, work_state=state)
            if (
                self._dependencies.identity is not None
                and "provenance" in catalogue_payload
            ):
                identity = deepcopy(self._dependencies.identity())
                identity["required_action"] = (
                    "reconnect"
                    if identity["reload_required"]
                    else ("unknown" if identity["reload_required"] is None else "none")
                )
                catalogue_payload["provenance"].update(
                    {
                        "contract_version": 2,
                        "installed_build": identity["installed"]["build_id"],
                        "connected_host_build": identity["loaded"]["build_id"],
                        "core_identity": identity,
                    }
                )
            return catalogue_payload
        if name.startswith("pf.runtime_driver."):
            result, rows = self._drivers()
            if result.exit_code:
                return self._failure(name, result)
            if name.endswith(".list"):
                return {"schema_version": 1, "kind": name, "status": "ready", "drivers": rows}
            if arguments["driver"] not in {row["id"] for row in rows}:
                raise ActionToolError("driver_not_registered")
            driver_ref = self._dependencies.registered_driver_ref(arguments["driver"])
            result = self._invoke(["runtime-driver", "describe"], {"driver": driver_ref}, workplace=True)
            if result.exit_code:
                return self._failure(name, result)
            document = yaml.safe_load(result.stdout)
            if not isinstance(document, dict):
                raise ActionToolError("native_result_invalid")
            # Driver manifests may contain argv/environment values; return metadata only.
            metadata = {key: deepcopy(document[key]) for key in ("schema_version", "id", "name", "version", "status", "kind", "description") if key in document}
            return {"schema_version": 1, "kind": name, "status": "ready", "driver": metadata, "native_validation_required": True}
        if name in WORK_TOOL_NAMES:
            self._work(arguments, execution=name != "pf.worker.status")
            operation = name.rsplit(".", 1)[1]
            values: dict[str, Any] = {"task": arguments["assignment_id"]}
            if operation in {"prepare", "start"}:
                result, rows = self._drivers()
                if result.exit_code:
                    return self._failure(name, result)
                if arguments["driver"] not in {row["id"] for row in rows}:
                    raise ActionToolError("driver_not_registered")
                values["driver"] = self._dependencies.registered_driver_ref(arguments["driver"])
                values.update({key: arguments[key] for key in ("model", "reasoning_effort") if key in arguments})
            if operation == "start":
                values["detach"] = True
            result = self._invoke(["worker-run", operation], values)
            if result.exit_code:
                if operation == "status" and result.stdout.startswith("STATUS: not-prepared "):
                    return {"schema_version": 1, "kind": name, "status": "not_prepared", "work": {key: arguments[key] for key in ("run_id", "assignment_id", "context_id")}}
                return self._failure(name, result)
            payload: dict[str, Any] = {"schema_version": 1, "kind": name, "status": "accepted", "native_exit_code": 0,
                                       "work": {key: arguments[key] for key in ("run_id", "assignment_id", "context_id")}}
            if operation == "status":
                state = yaml.safe_load(result.stdout)
                if not isinstance(state, dict):
                    raise ActionToolError("native_result_invalid")
                payload["worker"] = state
                payload["status"] = "ready"
            else:
                payload["native_summary"] = result.stdout[-2000:].strip()
            return payload
        if name in SESSION_TOOL_NAMES:
            if not self._session_id:
                raise ActionToolError("missing_session")
            record = self._dependencies.session_record()
            if record.get("session_id") != self._session_id or not record.get("agent_id"):
                raise ActionToolError("unknown_session")
            if name == "pf.session.heartbeat":
                result = self._invoke(["session-heartbeat"], {"agent": record["agent_id"], "session": self._session_id}, workplace=True)
            else:
                result = self._invoke(["chat-record"], {"session_id": self._session_id, "participant": record["agent_id"], "participant_type": "agent",
                                                         "participant_role": "agent", "role": "assistant", "content": arguments["content"]})
            if result.exit_code:
                return self._failure(name, result)
            return {"schema_version": 1, "kind": name, "status": "completed", "session_id": self._session_id, "agent_id": record["agent_id"],
                    "native_summary": result.stdout[-2000:].strip()}
        raise ActionToolError("unknown_tool")
