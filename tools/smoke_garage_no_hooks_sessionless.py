#!/usr/bin/env python3
"""Smoke test for Garage context/search/resolve without hooks, session, or daemon."""

from __future__ import annotations

import json
import shutil
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
    lines = [json.loads(line) for line in result.stdout.splitlines() if line.strip()]
    response = lines[-1]
    text = response["result"]["content"][0]["text"]
    if response["result"].get("isError"):
        raise AssertionError(text)
    return json.loads(text)


def add_fixture_resource(project: Path) -> str:
    knowledge_root = project / "knowledge" / "articles"
    knowledge_root.mkdir(parents=True)
    (knowledge_root / "garage.md").write_text("GarageNoHooksNeedle proves sessionless PF search.", encoding="utf-8")
    snapshot_path = project / ".pf" / "contexts" / "project-context.snapshot.yaml"
    snapshot = yaml.safe_load(snapshot_path.read_text(encoding="utf-8"))
    resource = {
        "id": "fixture.docs:garage-article",
        "resource_id": "fixture.docs:garage-article",
        "package_id": "fixture.docs",
        "kind": "knowledge",
        "title": "Garage article",
        "content_roots": [str(knowledge_root)],
        "indexing": {"enabled": True, "mode": "fulltext", "sources": [{"path": ".", "mode": "fulltext", "include": ["*.md"], "exclude": []}]},
    }
    snapshot.setdefault("resolved", {}).setdefault("available_knowledge_resources", []).append(resource)
    snapshot["local_search_resources"] = [resource]
    snapshot_path.write_text(yaml.safe_dump(snapshot, allow_unicode=True, sort_keys=False), encoding="utf-8")
    return resource["id"]


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="pf-garage-no-hooks-") as raw:
        root = Path(raw)
        workplace = root / "workplace"
        project = root / "project"
        cli("workplace-init", "--workplace", str(workplace), "--apply")
        cli("project-onboard", "--project-root", str(project), "--workplace", str(workplace), "--type", "generic", "--apply")
        shutil.rmtree(project / ".codex", ignore_errors=True)
        resource_id = add_fixture_resource(project)

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
