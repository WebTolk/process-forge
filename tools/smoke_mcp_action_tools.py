#!/usr/bin/env python3
"""Exercise native action boundaries, identity failures and pre-dispatch schemas."""

from __future__ import annotations

import argparse
from copy import deepcopy
from pathlib import Path
import sys
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "tools"), str(ROOT / "src")]

from pf_runtime import mcp_server
from pf_runtime.action_tools import ActionToolDependencies, ActionToolError, ActionToolService
from pf_runtime.session_read import SessionReadError


IDENTITY = {"run_id": "run-a", "assignment_id": "task-a", "context_id": "capsule-a"}


class Fixture:
    def __init__(self) -> None:
        self.calls: list[list[str]] = []
        self.allow_driver_id = True
        self.state = {
            "run": {"id": "run-a", "status": "in_progress"},
            "assignment": {"id": "task-a", "status": "in_progress"},
            "context": {"id": "capsule-a", "validation": {"status": "valid"}},
            "execution_readiness": {"status": "ready"}, "blockers": [],
        }

    def work_state(self, **selectors):
        assert selectors == IDENTITY
        return deepcopy(self.state)

    def forbidden_parser(self):
        raise AssertionError("Native dispatch must use the complete CLI application callable")

    def native(self, argv: list[str]) -> int:
        self.calls.append(list(argv))
        if argv[:2] == ["runtime-driver", "list"]:
            print("codex-exec\tactive\tbuiltin")
            print("manual\tactive\tbuiltin")
        elif argv[:2] == ["runtime-driver", "describe"]:
            print("diagnostic on stderr", file=sys.stderr)
            print("id: codex-exec\nkind: shell\ncommand:\n  env:\n    PRIVATE_TOKEN: hidden-value")
        elif argv[:2] == ["worker-run", "start"]:
            assert "--detach" in argv
            assert "--driver=registered-driver.yaml" in argv
            assert not any(x.startswith("--executable") or x == "--wait" for x in argv)
            print("RUNNING: task-a pid=123")
        elif argv[:2] == ["worker-run", "status"]:
            print("status: running\nattempt: 2")
        elif argv[0] == "chat-record":
            assert "--participant=real-agent" in argv
            assert "--role=assistant" in argv
            assert "--content=--not-an-option" in argv
            print("MESSAGE: msg-a")
        elif argv[0] == "session-heartbeat":
            assert "--session=session-a" in argv
            assert "--agent=real-agent" in argv
            print("STATUS: active")
        else:
            print("PREPARED: task-a")
        return 0

    def registered_driver_ref(self, driver):
        assert driver == "codex-exec"
        if not self.allow_driver_id:
            raise ActionToolError("registered_driver_manifest_unavailable")
        return "registered-driver.yaml"

    def service(self, session="session-a"):
        dependencies = ActionToolDependencies(
            parser_factory=self.forbidden_parser, native_command=self.native,
            registered_driver_ref=self.registered_driver_ref,
            work_state=self.work_state,
            session_record=lambda: {"session_id": "session-a", "agent_id": "real-agent"},
            version="test",
        )
        return ActionToolService(dependencies, Path("project-a"), Path("workplace-a"), session)


def refused(service, name, arguments, reason):
    try:
        service.execute(name, arguments)
    except ActionToolError as exc:
        assert exc.code == reason, (exc.code, reason)
    else:
        raise AssertionError((name, "expected refusal", reason))


def main() -> int:
    f = Fixture()
    service = f.service()
    launch = {**IDENTITY, "driver": "codex-exec", "apply": True}
    for invalid, reason in [({**launch, "executable": "foreign.exe"}, "invalid_arguments"),
                            ({**launch, "apply": False}, "apply_required"),
                            ({"driver": "codex-exec", "apply": True}, "invalid_arguments")]:
        refused(service, "pf.worker.start", invalid, reason)
        assert not f.calls
    for terminal in ("completed", "failed", "cancelled"):
        f.state["run"]["status"] = terminal
        refused(service, "pf.worker.start", launch, "work_is_terminal")
        assert not f.calls
    f.state["run"]["status"] = "in_progress"
    f.state["context"]["id"] = "other-capsule"
    refused(service, "pf.worker.start", launch, "work_context_mismatch")
    assert not f.calls
    f.state["context"]["id"] = IDENTITY["context_id"]
    refused(service, "pf.actions.list", {"run_id": "run-a"}, "work_selectors_required")
    assert not f.calls
    refused(service, "pf.chat.record", {"content": "hello", "participant": "operator", "apply": True}, "invalid_arguments")
    refused(f.service(session=""), "pf.chat.record", {"content": "hello", "apply": True}, "missing_session")
    assert not f.calls

    refused(service, "pf.worker.start", {**launch, "driver": "other/driver.yaml"}, "driver_not_registered")
    assert len(f.calls) == 1 and f.calls[0][:2] == ["runtime-driver", "list"]
    f.calls.clear()
    f.allow_driver_id = False
    for name, arguments in [("pf.runtime_driver.describe", {"driver": "codex-exec"}),
                            ("pf.worker.prepare", launch), ("pf.worker.start", launch)]:
        refused(service, name, arguments, "registered_driver_manifest_unavailable")
        assert all(argv[:2] == ["runtime-driver", "list"] for argv in f.calls)
    f.calls.clear()
    f.allow_driver_id = True
    result = service.execute("pf.worker.start", {**launch, "model": "--literal-model"})
    assert result["status"] == "accepted" and "RUNNING" in result["native_summary"]
    assert f.calls[-1][:2] == ["worker-run", "start"] and "--model=--literal-model" in f.calls[-1]
    result = service.execute("pf.worker.status", {**IDENTITY, "apply": True})
    assert result["worker"]["status"] == "running"
    assert mcp_server.tool_annotations("pf.worker.status")["readOnlyHint"] is False
    description = service.execute("pf.runtime_driver.describe", {"driver": "codex-exec"})
    assert description["driver"]["id"] == "codex-exec" and "hidden-value" not in str(description)
    service.execute("pf.chat.record", {"content": "--not-an-option", "apply": True})
    service.execute("pf.session.heartbeat", {"apply": True})

    # The published array maxima must stop requests before business dispatch.
    original = mcp_server.tool_result
    dispatched = []
    mcp_server.tool_result = lambda *args: dispatched.append(args) or {"status": "inert"}
    runtime = SimpleNamespace(core=SimpleNamespace())
    cases = [
        ("pf.continuation.create", {**IDENTITY, "continuation_id": "cont", "expected_artifacts": []}, "expected_artifacts", 128, "artifact"),
        ("pf.work.cancel", {**IDENTITY, "capsule_checksum": "seal", "reason": "test", "evidence": []}, "evidence", 128, "evidence"),
        ("pf.project_initialization.initialize", {"apply": True, "entry_budget_policy": []}, "entry_budget_policy", 32, {}),
        ("pf.project_initialization.repair", {"apply": True, "repair_action": "refresh_context", "entry_budget_policy": []}, "entry_budget_policy", 32, {}),
    ]
    try:
        for name, arguments, key, limit, value in cases:
            for size in (limit, limit + 1):
                args = {**arguments, key: [deepcopy(value) for _ in range(size)]}
                before = len(dispatched)
                request = {"jsonrpc": "2.0", "id": size, "method": "tools/call", "params": {"name": name, "arguments": args}}
                response = mcp_server._respond(request, Path("workplace"), "", runtime)
                if size == limit:
                    assert len(dispatched) == before + 1 and "error" not in response, response
                else:
                    assert len(dispatched) == before and response["error"]["code"] == -32602, response
        for name, arguments in [
            ("pf.actions.list", {"limit": 101}), ("pf.actions.list", {"query": "x" * 257}),
            ("pf.session.heartbeat", {"apply": True, "ttl": 100}),
            ("pf.worker.start", {**launch, "wait": True}),
        ]:
            before = len(dispatched)
            response = mcp_server._respond({"jsonrpc": "2.0", "id": 99, "method": "tools/call", "params": {"name": name, "arguments": arguments}}, Path("workplace"), "", runtime)
            assert response["error"]["code"] == -32602 and len(dispatched) == before, response
    finally:
        mcp_server.tool_result = original

    # Project/session mismatch fails before constructing or invoking a native action.
    host = SimpleNamespace(resolve_project=lambda value, core: Path(value),
                           project_for_session=lambda args, workplace, core: Path("bound-project"))
    runtime = SimpleNamespace(host=host, core=SimpleNamespace(project_id=lambda path: path.name))
    try:
        mcp_server._tool_result("pf.runtime_driver.list", {"project_root": "foreign-project"}, Path("workplace"), "session-a", runtime)
    except SessionReadError as exc:
        assert str(exc) == "session_project_mismatch", exc
    else:
        raise AssertionError("foreign project admitted")

    runtime.core.project_id = lambda path: "colliding-id"
    try:
        mcp_server._tool_result("pf.chat.record", {"project_root": "foreign-project", "content": "hello", "apply": True}, Path("workplace"), "session-a", runtime)
    except SessionReadError as exc:
        assert str(exc) == "session_project_mismatch", exc
    else:
        raise AssertionError("same-ID foreign physical project admitted")

    # The outer protocol entry must reject before optional diagnostic I/O too.
    from processforge_core import diagnostics
    diagnostic_attempts = []
    original_logger = diagnostics.for_project

    def observed_logger(*args, **kwargs):
        diagnostic_attempts.append(args)
        return original_logger(None)

    diagnostics.for_project = observed_logger
    try:
        for arguments, schema_error in [
            ({"project_root": "foreign-project", "content": "inert", "apply": True}, False),
            ({"project_root": "foreign-project", "content": "inert", "apply": True, "participant": "foreign"}, True),
        ]:
            response = mcp_server.respond({"jsonrpc": "2.0", "id": 100, "method": "tools/call", "params": {
                "name": "pf.chat.record", "arguments": arguments}}, Path("workplace"), "session-a", runtime)
            if schema_error:
                assert response["error"]["code"] == -32602, response
            else:
                assert response["result"].get("isError"), response
            assert not diagnostic_attempts, "rejected new-tool preflight constructed a diagnostic sink"
    finally:
        diagnostics.for_project = original_logger

    print("PASS: typed native MCP actions preserve binding, terminal/apply guards, literal arguments, driver metadata privacy and pre-dispatch schema bounds")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
