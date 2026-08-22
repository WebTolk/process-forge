"""Self-contained smoke for the snapshot-authorized SQLite FTS5 search core."""

from __future__ import annotations

import tempfile
import sys
import json
import subprocess
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "tools"))

from processforge_core.local_resource_search import LocalSearchError, search
import processforge as core


def main() -> int:
    with tempfile.TemporaryDirectory() as raw:
        project = Path(raw)
        allowed = project / "allowed"
        allowed.mkdir()
        (allowed / "guide.md").write_text("ProcessForge snapshot authorized local search", encoding="utf-8")
        outside = project / "outside.md"
        outside.write_text("forbidden-secret-token", encoding="utf-8")
        snapshot = {"snapshot": {"id": "smoke"}, "local_search_resources": [{"id": "docs", "package_id": "smoke", "kind": "knowledge", "content_roots": [str(allowed)]}]}
        result = search(project, snapshot, query="authorized", limit=1, limitstart=0)
        assert result["search_status"] == "missing"
        assert result["index_generation"]
        assert result["results"][0]["canonical_path"] == "guide.md"
        assert result["results"][0]["path_ref"] == "docs:guide.md"
        assert search(project, snapshot, query="authorized")["search_status"] == "fresh"
        changed = {"snapshot": {"id": "smoke-next"}, "local_search_resources": snapshot["local_search_resources"]}
        assert search(project, changed, query="authorized")["search_status"] == "stale"
        assert search(project, snapshot, query="forbidden-secret-token")["results"] == []
        try:
            search(project, snapshot, query="authorized", limitstart=1, offset=2)
        except LocalSearchError as exc:
            assert exc.code == "ambiguous_offset"
        else:
            raise AssertionError("conflicting pagination accepted")
    with tempfile.TemporaryDirectory(prefix="pf-mcp-stdio-smoke-") as raw:
        root = Path(raw)
        workplace, first, second = root / "workplace", root / "first", root / "second"
        first.mkdir()
        second.mkdir()
        allowed = first / "allowed"
        allowed.mkdir()
        (allowed / "guide.md").write_text("MCP snapshot authorized search", encoding="utf-8")
        external_docs = root / "external-docs"
        external_docs.mkdir()
        (external_docs / "external-guide.md").write_text("External knowledge root search proof", encoding="utf-8")
        (root / "outside.md").write_text("traversal-secret-token registry-secret-token", encoding="utf-8")
        def cli(*args: str) -> str:
            result = subprocess.run([sys.executable, str(ROOT / "tools" / "processforge.py"), *args], cwd=ROOT, text=True, encoding="utf-8", errors="replace", capture_output=True)
            assert result.returncode == 0, result.stdout + result.stderr
            return result.stdout
        cli("workplace-init", "--workplace", str(workplace), "--apply")
        knowledge_roots_path = workplace / "registries" / "knowledge-roots.yaml"
        knowledge_roots = yaml.safe_load(knowledge_roots_path.read_text(encoding="utf-8"))
        knowledge_roots["knowledge_roots"].append({"id": "external-docs", "path": str(external_docs), "scope": "workplace", "status": "available"})
        knowledge_roots_path.write_text(yaml.safe_dump(knowledge_roots, allow_unicode=True, sort_keys=False), encoding="utf-8")
        cli("template-create", "--workplace", str(workplace), "--id", "joomla-plugin-manifest", "--title", "Joomla Plugin Manifest", "--apply")
        registry_path = workplace / "registries" / "templates.yaml"
        registry = yaml.safe_load(registry_path.read_text(encoding="utf-8"))
        registry["templates"].append({"id": "escaped-template", "title": "Escaped Template", "path": "../outside.md", "status": "available"})
        registry_path.write_text(yaml.safe_dump(registry, allow_unicode=True, sort_keys=False), encoding="utf-8")
        cli("project-onboard", "--project-root", str(first), "--workplace", str(workplace), "--type", "generic", "--apply")
        cli("project-onboard", "--project-root", str(second), "--workplace", str(workplace), "--type", "generic", "--apply")
        cli("agent-checkin", "--workplace", str(workplace), "--agent", "smoke-agent", "--session", "smoke-session", "--project-root", str(first), "--role", "worker")
        manifest_path = first / ".pf" / "process-forge.yaml"
        manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
        manifest["context_requirements"]["templates"] = [{"id": "joomla-plugin-manifest", "required": False}, {"id": "escaped-template", "required": False}]
        manifest_path.write_text(yaml.safe_dump(manifest, allow_unicode=True, sort_keys=False), encoding="utf-8")
        cli("project-context-refresh", "--project-root", str(first), "--workplace", str(workplace), "--apply")
        snapshot_path = first / ".pf" / "contexts" / "project-context.snapshot.yaml"
        snapshot = yaml.safe_load(snapshot_path.read_text(encoding="utf-8"))
        assert any(item.get("kind") == "template" for item in snapshot["local_search_resources"] if isinstance(item, dict))
        assert str(workplace) not in snapshot_path.read_text(encoding="utf-8")
        assert all(not set(item).intersection({"content_roots", "local_path", "resolved_path"}) for item in snapshot["local_search_resources"] if isinstance(item, dict))
        snapshot["local_search_resources"].extend([
            {"id": "allowed", "package_id": "self", "kind": "knowledge", "path_ref": {"package": "self", "relative_path": "allowed"}},
            {"id": "escaped", "package_id": "self", "kind": "knowledge", "path_ref": {"package": "self", "relative_path": "../outside.md"}},
            {"id": "external", "package_id": "fixture", "kind": "knowledge", "path_ref": {"registry": "knowledge_roots", "id": "external-docs"}},
            {"id": "external-escaped", "package_id": "fixture", "kind": "knowledge", "path_ref": {"registry": "knowledge_roots", "id": "external-docs", "relative_path": "../outside.md"}},
        ])
        snapshot_path.write_text(yaml.safe_dump(snapshot, allow_unicode=True, sort_keys=False), encoding="utf-8")
        external_resolution = core.resolve_workspace_path_ref(first, {"registry": "knowledge_roots", "id": "external-docs"}, workplace_manifest=workplace / "workplace.yaml")
        assert external_resolution == {"status": "resolved", "path": str(external_docs)}
        escaped_resolution = core.resolve_workspace_path_ref(first, {"registry": "knowledge_roots", "id": "external-docs", "relative_path": "../outside.md"}, workplace_manifest=workplace / "workplace.yaml")
        assert escaped_resolution["status"] == "unresolved"
        status_output = cli("search-index", "status", "--project-root", str(first), "--workplace", str(workplace))
        assert "STATUS: missing" in status_output or "STATUS: stale" in status_output
        refresh_output = cli("search-index", "refresh", "--project-root", str(first), "--workplace", str(workplace))
        assert "REFRESHED:" in refresh_output and "DOCUMENTS:" in refresh_output
        doctor_output = cli("search-index", "doctor", "--project-root", str(first), "--workplace", str(workplace))
        assert "PASS: SQLite FTS5 available" in doctor_output
        noop_tick = cli("search-index", "tick", "--project-root", str(first), "--workplace", str(workplace))
        assert "ACTION: none" in noop_tick
        (allowed / "guide.md").write_text("MCP snapshot authorized search maintenancetoken", encoding="utf-8")
        verified_status = cli("search-index", "status", "--project-root", str(first), "--workplace", str(workplace), "--verify-files")
        assert "STATUS: stale" in verified_status and "document_fingerprint_changed" in verified_status
        refresh_tick = cli("search-index", "tick", "--project-root", str(first), "--workplace", str(workplace))
        assert "ACTION: refresh" in refresh_tick and "STATUS: fresh" in refresh_tick
        requests = [
            {"jsonrpc": "2.0", "id": 1, "method": "initialize"},
            {"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
            {"jsonrpc": "2.0", "id": 3, "method": "tools/call", "params": {"name": "pf.search", "arguments": {"session_id": "smoke-session", "query": "authorized"}}},
            {"jsonrpc": "2.0", "id": 4, "method": "tools/call", "params": {"name": "pf.project_initialization.status", "arguments": {"session_id": "smoke-session", "project_root": str(second)}}},
            {"jsonrpc": "2.0", "id": 5, "method": "tools/call", "params": {"name": "pf.search", "arguments": {"session_id": "smoke-session", "query": "traversal-secret-token"}}},
            {"jsonrpc": "2.0", "id": 6, "method": "tools/call", "params": {"name": "pf.search", "arguments": {"session_id": "smoke-session", "query": "External knowledge root"}}},
            {"jsonrpc": "2.0", "id": 7, "method": "tools/call", "params": {"name": "pf.search", "arguments": {"session_id": "smoke-session", "query": "maintenancetoken"}}},
            {"jsonrpc": "2.0", "id": 8, "method": "tools/call", "params": {"name": "pf.project_initialization.repair", "arguments": {"session_id": "smoke-session"}}},
            {"jsonrpc": "2.0", "id": 9, "method": "tools/call", "params": {"name": "pf.project_initialization.repair", "arguments": {"session_id": "smoke-session", "apply": True, "reason": "stdio-smoke"}}},
            {"jsonrpc": "2.0", "id": 10, "method": "tools/call", "params": {"name": "pf.project_initialization.initialize", "arguments": {"session_id": "smoke-session", "apply": True, "answers_path": str(root / "outside.md")}}},
            {"jsonrpc": "2.0", "id": 11, "method": "tools/call", "params": {"name": "pf.search", "arguments": {"session_id": "smoke-session", "query": "Joomla Plugin Manifest"}}},
            {"jsonrpc": "2.0", "id": 12, "method": "tools/call", "params": {"name": "pf.search", "arguments": {"session_id": "smoke-session", "query": "registry-secret-token"}}},
            {"jsonrpc": "2.0", "id": 13, "method": "tools/call", "params": {"name": "pf.session_context", "arguments": {"session_id": "smoke-session"}}},
        ]
        result = subprocess.run([sys.executable, str(ROOT / "tools" / "pf_runtime" / "mcp_server.py"), "--workplace", str(workplace), "--session", "smoke-session"], cwd=ROOT, text=True, encoding="utf-8", errors="replace", input="\n".join(json.dumps(item) for item in requests) + "\n", capture_output=True)
        assert result.returncode == 0, result.stderr
        responses = [json.loads(line) for line in result.stdout.splitlines() if line.strip()]
        assert responses[0]["result"]["serverInfo"]["name"] == "processforge"
        assert "pf.search" in [item["name"] for item in responses[1]["result"]["tools"]]
        search_result = json.loads(responses[2]["result"]["content"][0]["text"])
        assert search_result["results"][0]["canonical_path"] == "guide.md"
        assert str(allowed) not in responses[2]["result"]["content"][0]["text"]
        assert responses[3]["result"]["isError"] is True
        assert json.loads(responses[3]["result"]["content"][0]["text"])["error"]["code"] == "session_project_mismatch"
        escaped_result = json.loads(responses[4]["result"]["content"][0]["text"])
        assert escaped_result["results"] == []
        external_result = json.loads(responses[5]["result"]["content"][0]["text"])
        assert external_result["results"], external_result
        assert external_result["results"][0]["provenance"]["package_id"] == "fixture"
        assert Path(external_result["results"][0]["local_path"]).is_file()
        maintenance_result = json.loads(responses[6]["result"]["content"][0]["text"])
        assert maintenance_result["results"] and maintenance_result["results"][0]["canonical_path"] == "guide.md", maintenance_result
        assert responses[7]["result"]["isError"] is True
        assert json.loads(responses[7]["result"]["content"][0]["text"])["error"]["code"] == "apply_required"
        repair_result = json.loads(responses[8]["result"]["content"][0]["text"])
        assert repair_result["action"] == "repair" and repair_result["applied"] is True
        assert repair_result["result"]["doctor"]["status"] == "pass"
        assert responses[9]["result"]["isError"] is True
        assert json.loads(responses[9]["result"]["content"][0]["text"])["error"]["code"] == "invalid_arguments"
        template_result = json.loads(responses[10]["result"]["content"][0]["text"])
        assert template_result["results"][0]["provenance"]["kind"] == "template"
        assert Path(template_result["results"][0]["local_path"]).is_file()
        assert json.loads(responses[11]["result"]["content"][0]["text"])["results"] == []
        session_context = json.loads(responses[12]["result"]["content"][0]["text"])
        assert session_context["search"]["status"] == "fresh"
        assert session_context["search"]["generation"]
        assert (workplace / "runtime" / "search" / "local-resource-search.sqlite").is_file()
        assert not (first / ".pf" / "runtime" / "local-resource-search" / "search.sqlite").exists()
        public_report = (first / ".pf" / "artifacts" / "project-onboarding-report.md").read_text(encoding="utf-8")
        assert str(first) not in public_report and "full doctor diagnostic is intentionally not copied" in public_report
    print("PASS: snapshot-authorized SQLite FTS5 search smoke")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
