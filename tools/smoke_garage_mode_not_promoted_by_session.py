#!/usr/bin/env python3
"""Smoke test that a bound session does not promote Garage to Forge."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

import yaml


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
    with tempfile.TemporaryDirectory(prefix="pf-garage-mode-") as raw:
        root = Path(raw)
        workplace = root / "workplace"
        project = root / "project"
        cli("workplace-init", "--workplace", str(workplace), "--apply")
        cli("project-onboard", "--project-root", str(project), "--workplace", str(workplace), "--type", "generic", "--apply")
        cli("agent-checkin", "--workplace", str(workplace), "--agent", "fixture-agent", "--session", "fixture-session", "--project-root", str(project))
        sessionless = call_mcp(workplace, "pf.context", {"project_root": str(project)})
        bound = call_mcp(workplace, "pf.context", {"project_root": str(project), "session_id": "fixture-session"})
        if sessionless.get("mode") != "garage" or sessionless.get("session", {}).get("status") != "absent":
            raise AssertionError(sessionless)
        if bound.get("mode") != "garage" or bound.get("session", {}).get("status") != "bound":
            raise AssertionError(bound)
        snapshot_path = project / ".pf" / "contexts" / "project-context.snapshot.yaml"
        snapshot = yaml.safe_load(snapshot_path.read_text(encoding="utf-8"))
        snapshot["workplace_coordination"] = {
            "project_mode": "organized",
            "workplace_default_project_mode": "simple",
            "effective_mode": "organized",
            "director_required": True,
            "director_available_at_workplace": False,
            "director_office_exists": False,
        }
        snapshot_path.write_text(yaml.safe_dump(snapshot, allow_unicode=True, sort_keys=False), encoding="utf-8")
        forge = call_mcp(workplace, "pf.context", {"project_root": str(project)})
        if forge.get("mode") != "forge":
            raise AssertionError(forge)
        codes = {item.get("code") for item in forge.get("diagnostics", []) if isinstance(item, dict)}
        if "forge_runtime_required_but_unavailable" not in codes:
            raise AssertionError(forge)
    print("PASS: bound session enriches Garage without promoting mode")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
