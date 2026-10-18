#!/usr/bin/env python3
"""Smoke test for sessionless and session-aware cross-project resource isolation."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PF = ROOT / "tools" / "processforge.py"
MCP = ROOT / "tools" / "pf_runtime" / "mcp_server.py"
TMP_ROOT = ROOT / ".pf" / "tmp" / "core-f01-f02-20260910" / "f01-search"
sys.path.insert(0, str(ROOT / "tools"))

from garage_search_smoke_support import empty_fixture_authorization, register_fixture_resource, run_cli, select_fixture_resource


def call_mcp(workplace: Path, name: str, arguments: dict[str, object], *, expect_error: bool = False) -> dict[str, object]:
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
        if expect_error:
            return json.loads(text)
        raise AssertionError(text)
    if expect_error:
        raise AssertionError(text)
    return json.loads(text)


def main() -> int:
    TMP_ROOT.mkdir(parents=True, exist_ok=True)
    root = TMP_ROOT / f"cross-project-{os.getpid()}"
    root.mkdir(parents=True, exist_ok=True)
    workplace = root / "workplace"
    project_a = root / "project-a"
    project_b = root / "project-b"
    run_cli("workplace-init", "--workplace", str(workplace), "--apply")
    resource_a = register_fixture_resource(
        workplace,
        "fixture.docs.a",
        "a",
        {"one.md": "SharedGarageNeedle ProjectANeedle", "two.md": "SharedGarageNeedle ProjectASecondNeedle"},
        title="Fixture A",
    )
    resource_b = register_fixture_resource(
        workplace,
        "fixture.docs.b",
        "b",
        {"one.md": "SharedGarageNeedle ProjectBNeedle", "two.md": "SharedGarageNeedle ProjectBSecondNeedle"},
        title="Fixture B",
    )
    run_cli("project-onboard", "--project-root", str(project_a), "--workplace", str(workplace), "--type", "generic", "--apply")
    run_cli("project-onboard", "--project-root", str(project_b), "--workplace", str(workplace), "--type", "generic", "--apply")
    select_fixture_resource(project_a, workplace, "fixture.docs.a", "a")
    select_fixture_resource(project_b, workplace, "fixture.docs.b", "b")

    positive_b = call_mcp(workplace, "pf.search", {"project_root": str(project_b), "query": "ProjectBNeedle"})
    if positive_b.get("total") != 1 or positive_b.get("results", [{}])[0].get("resource_id") != resource_b:
        raise AssertionError(positive_b)
    shared_page_0 = call_mcp(workplace, "pf.search", {"project_root": str(project_a), "query": "SharedGarageNeedle", "limit": 1, "offset": 0})
    shared_page_1 = call_mcp(workplace, "pf.search", {"project_root": str(project_a), "query": "SharedGarageNeedle", "limit": 1, "offset": 1})
    if shared_page_0.get("total") != 2 or len(shared_page_0.get("results", [])) != 1 or len(shared_page_1.get("results", [])) != 1:
        raise AssertionError({"page0": shared_page_0, "page1": shared_page_1})
    if any(item.get("resource_id") != resource_a for item in shared_page_0.get("results", []) + shared_page_1.get("results", [])):
        raise AssertionError({"page0": shared_page_0, "page1": shared_page_1})
    search_a_for_b = call_mcp(workplace, "pf.search", {"project_root": str(project_a), "query": "ProjectBNeedle"})
    if search_a_for_b.get("total") != 0 or search_a_for_b.get("results") != []:
        raise AssertionError(search_a_for_b)
    positive_b_after_a = call_mcp(workplace, "pf.search", {"project_root": str(project_b), "query": "ProjectBNeedle"})
    if positive_b_after_a.get("total") != 1 or positive_b_after_a.get("results", [{}])[0].get("resource_id") != resource_b:
        raise AssertionError(positive_b_after_a)
    empty_project = root / "project-empty"
    run_cli("project-onboard", "--project-root", str(empty_project), "--workplace", str(workplace), "--type", "generic", "--apply")
    empty_fixture_authorization(empty_project, workplace)
    empty = call_mcp(workplace, "pf.search", {"project_root": str(empty_project), "query": "SharedGarageNeedle"})
    if empty.get("total") != 0 or empty.get("results") != []:
        raise AssertionError(empty)
    denied = call_mcp(workplace, "pf.resolve", {"project_root": str(project_a), "resource_id": resource_b})
    if denied.get("resource", {}).get("status") != "denied":
        raise AssertionError(denied)
    run_cli("agent-checkin", "--workplace", str(workplace), "--agent", "fixture-agent", "--session", "session-a", "--project-root", str(project_a))
    mismatch = call_mcp(workplace, "pf.search", {"project_root": str(project_b), "session_id": "session-a", "query": "ProjectBNeedle"}, expect_error=True)
    if mismatch.get("error", {}).get("code") != "session_project_mismatch":
        raise AssertionError(mismatch)
    print("PASS: Garage resource authorization is snapshot-bound across projects")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
