#!/usr/bin/env python3
"""Focused proof for Ledger authority, Codex adapter, and read-only MCP."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
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
    with tempfile.TemporaryDirectory(prefix="pf-ledger-hooks-mcp-") as temp:
        root, workplace = Path(temp), Path(temp) / "workplace"
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
        if json.loads(adapter.stdout).get("status") != "delivered":
            raise AssertionError("Codex adapter did not deliver a documented tool event")

        request = "\n".join([json.dumps({"jsonrpc": "2.0", "id": 1, "method": "initialize"}), json.dumps({"jsonrpc": "2.0", "id": 2, "method": "tools/call", "params": {"name": "pf.project_state", "arguments": {}}})]) + "\n"
        server = subprocess.run([sys.executable, str(ROOT / "tools" / "pf_runtime" / "mcp_server.py"), "--workplace", str(workplace), "--session", "sess-a"], input=request, text=True, capture_output=True, cwd=ROOT, check=True)
        responses = [json.loads(line) for line in server.stdout.splitlines() if line.strip()]
        if len(responses) != 2 or "result" not in responses[1]:
            raise AssertionError("MCP bridge did not return project state")

        denied_request = "\n".join([json.dumps({"jsonrpc": "2.0", "id": 1, "method": "initialize"}), json.dumps({"jsonrpc": "2.0", "id": 2, "method": "tools/call", "params": {"name": "pf.project_state", "arguments": {"project_root": str(second)}}})]) + "\n"
        denied_server = subprocess.run([sys.executable, str(ROOT / "tools" / "pf_runtime" / "mcp_server.py"), "--workplace", str(workplace), "--session", "sess-a"], input=denied_request, text=True, capture_output=True, cwd=ROOT, check=True)
        denied_responses = [json.loads(line) for line in denied_server.stdout.splitlines() if line.strip()]
        if not denied_responses[-1].get("result", {}).get("isError"):
            raise AssertionError("MCP accepted cross-project project_root")

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
    print("PASS: Runtime Ledger, Codex adapter, and MCP smoke")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
