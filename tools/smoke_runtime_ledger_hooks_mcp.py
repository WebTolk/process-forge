#!/usr/bin/env python3
"""Focused proof for Ledger authority, Codex adapter, and read-only MCP."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
import uuid
from pathlib import Path

from processforge_subprocess import diagnostic_text, run_command


ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "tools" / "processforge.py"


def pf(*args: str, expect: int = 0) -> str:
    result = run_command([sys.executable, str(CLI), *args], cwd=ROOT, timeout=120)
    if result.returncode != expect:
        raise AssertionError(f"expected {expect}: {' '.join(args)}\n{diagnostic_text(result)}")
    return result.stdout if expect == 0 else result.stdout + result.stderr


def project(root: Path, name: str, workplace: Path) -> Path:
    value = root / name
    value.mkdir()
    (value / "README.md").write_text("# test\n", encoding="utf-8")
    pf("project-onboard", "--project-root", str(value), "--workplace", str(workplace), "--type", "generic-software-project", "--apply")
    return value


def event(path: Path, project_root: Path, session: str, agent: str, event_type: str = "agent.session.started") -> Path:
    path.write_text(json.dumps({"schema_version": 1, "event_id": f"{session}-{event_type}", "event_type": event_type, "project_root": str(project_root), "session_id": session, "agent_id": agent, "source": {"adapter": "smoke", "session_id": session, "agent": agent}}), encoding="utf-8")
    return path


def main() -> int:
    tmp_root = ROOT / ".pf" / "tmp"
    tmp_root.mkdir(parents=True, exist_ok=True)
    root = tmp_root / f"pf-ledger-hooks-mcp-{uuid.uuid4().hex}"
    root.mkdir()
    try:
        workplace = root / "workplace"
        pf("workplace-init", "--workplace", str(workplace), "--apply")
        first, second = project(root, "first", workplace), project(root, "second", workplace)
        pf("runtime-host", "event", "--workplace", str(workplace), "--input", str(event(root / "a.json", first, "sess-a", "codex")))
        pf("runtime-host", "event", "--workplace", str(workplace), "--input", str(event(root / "b.json", second, "sess-b", "codex")))

        (workplace / "runtime" / "pf-runtime-host" / "state.json").unlink()
        routed = json.loads(pf("runtime-host", "project-state", "--workplace", str(workplace), "--session", "sess-a", "--json"))
        if routed["project"]["project_id"] == "second":
            raise AssertionError("Ledger routing recovered the wrong project")
        denied = pf("runtime-host", "event", "--workplace", str(workplace), "--input", str(event(root / "wrong.json", second, "sess-a", "codex", "agent.command.completed")), expect=1)
        if "not authorized" not in denied:
            raise AssertionError("cross-project event was not denied")

        hook = {"hook_event_name": "PostToolUse", "cwd": str(first), "session_id": "sess-a", "turn_id": "turn-1", "tool_name": "Bash", "tool_use_id": "tool-1"}
        adapter_env = dict(os.environ)
        adapter_env["PF_CODEX_HOOK_DEBUG"] = "1"
        adapter = subprocess.run([sys.executable, str(ROOT / "tools" / "pf_runtime" / "codex_hooks.py")], input=json.dumps(hook), text=True, capture_output=True, cwd=ROOT, env=adapter_env, check=True)
        if json.loads(adapter.stderr).get("status") != "delivered" or adapter.stdout:
            raise AssertionError("Codex adapter did not deliver a documented tool event")

        clear_hook = {"hook_event_name": "SessionStart", "source": "clear", "cwd": str(first), "session_id": "sess-clear"}
        clear_adapter = subprocess.run([sys.executable, str(ROOT / "tools" / "pf_runtime" / "codex_hooks.py")], input=json.dumps(clear_hook), text=True, capture_output=True, cwd=ROOT, env=adapter_env, check=True)
        if "ProcessForge session id: sess-clear" not in clear_adapter.stdout:
            raise AssertionError("Codex clear session did not receive a bound SessionStart handoff")

        request = "\n".join([
            json.dumps({"jsonrpc": "2.0", "id": 1, "method": "initialize"}),
            json.dumps({"jsonrpc": "2.0", "id": 2, "method": "tools/call", "params": {"name": "pf.project_state", "arguments": {}}}),
            json.dumps({"jsonrpc": "2.0", "id": 3, "method": "tools/call", "params": {"name": "pf.session_context", "arguments": {}}}),
            json.dumps({"jsonrpc": "2.0", "id": 4, "method": "tools/call", "params": {"name": "pf.session_chat", "arguments": {"limit": 5}}}),
            json.dumps({"jsonrpc": "2.0", "id": 5, "method": "tools/call", "params": {"name": "pf.session_activity", "arguments": {"limit": 5}}}),
        ]) + "\n"
        server = subprocess.run([sys.executable, str(ROOT / "tools" / "pf_runtime" / "mcp_server.py"), "--workplace", str(workplace), "--session", "sess-a"], input=request, text=True, capture_output=True, cwd=ROOT, check=True)
        responses = [json.loads(line) for line in server.stdout.splitlines() if line.strip()]
        if len(responses) != 5 or "result" not in responses[1]:
            raise AssertionError("MCP bridge did not return project state")
        context = json.loads(responses[2]["result"]["content"][0]["text"])
        chat = json.loads(responses[3]["result"]["content"][0]["text"])
        activity = json.loads(responses[4]["result"]["content"][0]["text"])
        if context.get("session", {}).get("id") != "sess-a" or chat.get("kind") != "pf.session_chat" or activity.get("kind") != "pf.session_activity":
            raise AssertionError("MCP session read models were not Ledger-bound")

        denied_request = "\n".join([json.dumps({"jsonrpc": "2.0", "id": 1, "method": "initialize"}), json.dumps({"jsonrpc": "2.0", "id": 2, "method": "tools/call", "params": {"name": "pf.project_state", "arguments": {"project_root": str(second)}}})]) + "\n"
        denied_server = subprocess.run([sys.executable, str(ROOT / "tools" / "pf_runtime" / "mcp_server.py"), "--workplace", str(workplace), "--session", "sess-a"], input=denied_request, text=True, capture_output=True, cwd=ROOT, check=True)
        denied_responses = [json.loads(line) for line in denied_server.stdout.splitlines() if line.strip()]
        if not denied_responses[-1].get("result", {}).get("isError"):
            raise AssertionError("MCP accepted cross-project project_root")

        missing_request = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {"name": "pf.session_context", "arguments": {}}}) + "\n"
        missing_server = subprocess.run([sys.executable, str(ROOT / "tools" / "pf_runtime" / "mcp_server.py"), "--workplace", str(workplace)], input=missing_request, text=True, capture_output=True, cwd=ROOT, check=True)
        missing_response = json.loads(missing_server.stdout)
        missing_error = json.loads(missing_response["result"]["content"][0]["text"])
        if missing_error != {"error": {"code": "missing_session"}}:
            raise AssertionError("MCP session error leaked details or used an unstable code")

        mismatch_request = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {"name": "pf.session_context", "arguments": {"project_root": str(second)}}}) + "\n"
        mismatch_server = subprocess.run([sys.executable, str(ROOT / "tools" / "pf_runtime" / "mcp_server.py"), "--workplace", str(workplace), "--session", "sess-a"], input=mismatch_request, text=True, capture_output=True, cwd=ROOT, check=True)
        mismatch_response = json.loads(mismatch_server.stdout)
        mismatch_error = json.loads(mismatch_response["result"]["content"][0]["text"])
        if mismatch_error != {"error": {"code": "session_project_mismatch"}}:
            raise AssertionError("MCP session context did not fail closed on project mismatch")

        switch_request = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {"name": "pf.session_context", "arguments": {"session_id": "sess-b"}}}) + "\n"
        switch_server = subprocess.run([sys.executable, str(ROOT / "tools" / "pf_runtime" / "mcp_server.py"), "--workplace", str(workplace), "--session", "sess-a"], input=switch_request, text=True, capture_output=True, cwd=ROOT, check=True)
        switch_response = json.loads(switch_server.stdout)
        switch_error = json.loads(switch_response["result"]["content"][0]["text"])
        if switch_error != {"error": {"code": "session_mismatch"}}:
            raise AssertionError("MCP process allowed its configured session to be overridden")

        pf("runtime", "start", "--workplace", str(workplace), "--timeout", "10")
        service_path = workplace / "runtime" / "pf-runtime" / "service.json"
        for _ in range(40):
            state = json.loads(service_path.read_text(encoding="utf-8")) if service_path.is_file() else {}
            if state.get("endpoint"):
                break
            time.sleep(0.1)
        else:
            raise AssertionError("Runtime did not publish an endpoint")
        try:
            urllib.request.urlopen(urllib.request.Request(str(state["endpoint"]).rstrip("/") + "/shutdown", data=b"{}", method="POST"), timeout=3)
        except urllib.error.HTTPError as exc:
            if exc.code != 401:
                raise AssertionError(f"unauthorized shutdown returned {exc.code}") from exc
        else:
            raise AssertionError("Runtime accepted an unauthorized shutdown")
        pf("runtime", "stop", "--workplace", str(workplace), "--timeout", "10")
    finally:
        shutil.rmtree(root, ignore_errors=True)
    print("PASS: Runtime Ledger, Codex adapter, and MCP smoke")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
