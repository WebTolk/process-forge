#!/usr/bin/env python3
"""Smoke test for the user-like Garage path without infrastructure instructions."""

from smoke_garage_mode_not_promoted_by_session import call_mcp, cli

import json
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MCP = ROOT / "tools" / "pf_runtime" / "mcp_server.py"


def tools_list(workplace: Path) -> list[str]:
    request = {"jsonrpc": "2.0", "id": 1, "method": "tools/list"}
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
    return [item["name"] for item in response["result"]["tools"]]


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="pf-user-like-") as raw:
        root = Path(raw)
        workplace = root / "workplace"
        project = root / "project"
        cli("workplace-init", "--workplace", str(workplace), "--apply")
        cli("project-onboard", "--project-root", str(project), "--workplace", str(workplace), "--type", "generic", "--apply")
        listed = tools_list(workplace)
        for required in ["pf.context", "pf.search", "pf.resolve", "pf.work.start"]:
            if required not in listed:
                raise AssertionError(listed)
        context = call_mcp(workplace, "pf.context", {"project_root": str(project)})
        project_id = context.get("project", {}).get("id")
        search = call_mcp(workplace, "pf.search", {"project_root": str(project), "query": "project-profile"})
        resolved = call_mcp(workplace, "pf.resolve", {"project_root": str(project), "resource_id": f"project.{project_id}:project-profile"})
        work = call_mcp(workplace, "pf.work.start", {"project_root": str(project), "objective": "Perform task from task.md"})
        if context.get("mode") != "garage" or search.get("total") != 1:
            raise AssertionError({"context": context, "search": search})
        if resolved.get("resource", {}).get("status") != "available":
            raise AssertionError(resolved)
        if work.get("action") != "created_new":
            raise AssertionError(work)
    print("PASS: user-like Garage path reaches governed work without manual infrastructure")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
