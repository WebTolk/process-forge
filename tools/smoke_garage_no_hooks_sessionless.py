#!/usr/bin/env python3
"""Smoke test for Garage context/search/resolve without hooks, session, or daemon."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PF = ROOT / "tools" / "processforge.py"
MCP = ROOT / "tools" / "pf_runtime" / "mcp_server.py"
sys.path.insert(0, str(ROOT / "tools"))

from garage_search_smoke_support import register_fixture_resource, run_cli, select_fixture_resource


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
    lines = [json.loads(line) for line in result.stdout.splitlines() if line.strip()]
    response = lines[-1]
    text = response["result"]["content"][0]["text"]
    if response["result"].get("isError"):
        raise AssertionError(text)
    return json.loads(text)


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="pf-garage-no-hooks-") as raw:
        root = Path(raw)
        workplace = root / "workplace"
        project = root / "project"
        run_cli("workplace-init", "--workplace", str(workplace), "--apply")
        resource_id = register_fixture_resource(
            workplace,
            "fixture.search-nohooks",
            "garage-article",
            {"garage.md": "GarageNoHooksNeedle proves sessionless PF search."},
            title="Garage article",
        )
        run_cli("project-onboard", "--project-root", str(project), "--workplace", str(workplace), "--type", "generic", "--apply")
        shutil.rmtree(project / ".codex", ignore_errors=True)
        select_fixture_resource(project, workplace, "fixture.search-nohooks", "garage-article")

        context = call_mcp(workplace, "pf.context", {"project_root": str(project)})
        if context.get("kind") != "pf.context" or context.get("context", {}).get("status") != "fresh":
            raise AssertionError(context)
        search = call_mcp(workplace, "pf.search", {"project_root": str(project), "query": "GarageNoHooksNeedle"})
        if search.get("total") != 1 or search.get("results", [{}])[0].get("resource_id") != resource_id:
            raise AssertionError(search)
        resolved = call_mcp(workplace, "pf.resolve", {"project_root": str(project), "resource_id": resource_id})
        if resolved.get("resource", {}).get("status") != "available":
            raise AssertionError(resolved)
        print("PASS: Garage context/search/resolve work without hooks, session, or daemon")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
