#!/usr/bin/env python3
"""Smoke test that a Ledger session enhances Garage without changing authorization."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

from garage_search_smoke_support import register_fixture_resource, select_fixture_resource


ROOT = Path(__file__).resolve().parents[1]
PF = ROOT / "tools" / "processforge.py"
MCP = ROOT / "tools" / "pf_runtime" / "mcp_server.py"


def cli(*args: str) -> subprocess.CompletedProcess[str]:
    result = subprocess.run([sys.executable, str(PF), *args], cwd=ROOT, text=True, encoding="utf-8", capture_output=True, timeout=120)
    if result.returncode != 0:
        raise AssertionError(result.stdout + result.stderr)
    return result


def call_mcp(workplace: Path, name: str, arguments: dict[str, object]) -> dict[str, object]:
    request = {"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {"name": name, "arguments": arguments}}
    result = subprocess.run(
        [sys.executable, str(MCP), "--workplace", str(workplace)],
        cwd=ROOT,
        text=True,
        encoding="utf-8",
        input=json.dumps({"jsonrpc": "2.0", "id": 0, "method": "initialize"}) + "\n" + json.dumps(request) + "\n",
        capture_output=True,
        timeout=120,
    )
    if result.returncode != 0:
        raise AssertionError(result.stderr)
    response = [json.loads(line) for line in result.stdout.splitlines() if line.strip()][-1]
    text = response["result"]["content"][0]["text"]
    if response["result"].get("isError"):
        raise AssertionError(text)
    return json.loads(text)


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="pf-garage-session-") as raw:
        root = Path(raw)
        workplace = root / "workplace"
        project = root / "project"
        cli("workplace-init", "--workplace", str(workplace), "--apply")
        resource_id = register_fixture_resource(
            workplace, "fixture.docs", "session",
            {"session.md": "GarageSessionNeedle proves stable authorization."},
            title="Session authorization fixture",
        )
        cli("project-onboard", "--project-root", str(project), "--workplace", str(workplace), "--type", "generic", "--apply")
        select_fixture_resource(project, workplace, "fixture.docs", "session")
        cli("agent-checkin", "--workplace", str(workplace), "--agent", "fixture-agent", "--session", "fixture-session", "--project-root", str(project))

        base = call_mcp(workplace, "pf.search", {"project_root": str(project), "query": "GarageSessionNeedle"})
        enhanced = call_mcp(workplace, "pf.search", {"project_root": str(project), "session_id": "fixture-session", "query": "GarageSessionNeedle"})
        if (base.get("total") != 1 or enhanced.get("total") != 1
                or not base.get("results") or not enhanced.get("results")
                or base["results"][0].get("resource_id") != resource_id
                or enhanced["results"][0].get("resource_id") != resource_id):
            raise AssertionError({"base": base, "enhanced": enhanced})
        context = call_mcp(workplace, "pf.context", {"project_root": str(project), "session_id": "fixture-session"})
        if context.get("mode") != "garage" or context.get("session", {}).get("status") != "bound" or context.get("session", {}).get("id") != "fixture-session":
            raise AssertionError(context)
    print("PASS: Garage session-aware mode preserves resource authorization")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
