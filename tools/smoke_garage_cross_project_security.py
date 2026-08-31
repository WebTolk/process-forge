#!/usr/bin/env python3
"""Smoke test for sessionless and session-aware cross-project resource isolation."""

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


def add_resource(project: Path, resource_id: str, needle: str) -> None:
    knowledge_root = project / "knowledge"
    knowledge_root.mkdir()
    (knowledge_root / "doc.md").write_text(needle, encoding="utf-8")
    snapshot_path = project / ".pf" / "contexts" / "project-context.snapshot.yaml"
    snapshot = yaml.safe_load(snapshot_path.read_text(encoding="utf-8"))
    resource = {
        "id": resource_id,
        "resource_id": resource_id,
        "package_id": "fixture.docs",
        "kind": "knowledge",
        "content_roots": [str(knowledge_root)],
        "indexing": {"enabled": True, "mode": "fulltext", "sources": [{"path": ".", "mode": "fulltext", "include": ["*.md"], "exclude": []}]},
    }
    snapshot.setdefault("resolved", {}).setdefault("available_knowledge_resources", []).append(resource)
    snapshot["local_search_resources"] = [resource]
    snapshot_path.write_text(yaml.safe_dump(snapshot, allow_unicode=True, sort_keys=False), encoding="utf-8")


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="pf-garage-security-") as raw:
        root = Path(raw)
        workplace = root / "workplace"
        project_a = root / "project-a"
        project_b = root / "project-b"
        cli("workplace-init", "--workplace", str(workplace), "--apply")
        cli("project-onboard", "--project-root", str(project_a), "--workplace", str(workplace), "--type", "generic", "--apply")
        cli("project-onboard", "--project-root", str(project_b), "--workplace", str(workplace), "--type", "generic", "--apply")
        add_resource(project_a, "fixture.docs:a", "ProjectANeedle")
        add_resource(project_b, "fixture.docs:b", "ProjectBNeedle")
        cli("agent-checkin", "--workplace", str(workplace), "--agent", "fixture-agent", "--session", "session-a", "--project-root", str(project_a))

        search_a_for_b = call_mcp(workplace, "pf.search", {"project_root": str(project_a), "query": "ProjectBNeedle"})
        if search_a_for_b.get("total") != 0:
            raise AssertionError(search_a_for_b)
        denied = call_mcp(workplace, "pf.resolve", {"project_root": str(project_a), "resource_id": "fixture.docs:b"})
        if denied.get("resource", {}).get("status") != "denied":
            raise AssertionError(denied)
        mismatch = call_mcp(workplace, "pf.search", {"project_root": str(project_b), "session_id": "session-a", "query": "ProjectBNeedle"}, expect_error=True)
        if mismatch.get("error", {}).get("code") != "session_project_mismatch":
            raise AssertionError(mismatch)
    print("PASS: Garage resource authorization is snapshot-bound across projects")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
