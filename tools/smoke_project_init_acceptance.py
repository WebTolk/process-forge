"""Acceptance smoke for project initialization, repair, FTS5, and session obligations.

The fixture deliberately uses a temporary workplace and projects.  It proves
the remaining master-prompt cases without changing this checkout's PF state.
"""

from __future__ import annotations

import json
import sqlite3
import subprocess
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

import yaml


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "tools"))

from processforge_core.local_resource_search import LocalSearchError, search
import processforge as core
from pf_runtime.session_read import session_context_payload


def cli(*args: str, cwd: Path = ROOT) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        [sys.executable, str(ROOT / "tools" / "processforge.py"), *args],
        cwd=cwd,
        text=True,
        encoding="utf-8",
        errors="strict",
        capture_output=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    return result


def mcp_session_context(workplace: Path, session_id: str) -> dict[str, object]:
    requests = [
        {"jsonrpc": "2.0", "id": 1, "method": "initialize"},
        {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/call",
            "params": {"name": "pf.session_context", "arguments": {"session_id": session_id}},
        },
    ]
    result = subprocess.run(
        [sys.executable, str(ROOT / "tools" / "pf_runtime" / "mcp_server.py"), "--workplace", str(workplace), "--session", session_id],
        cwd=ROOT,
        text=True,
        encoding="utf-8",
        errors="strict",
        input="\n".join(json.dumps(item) for item in requests) + "\n",
        capture_output=True,
    )
    assert result.returncode == 0, result.stderr
    responses = [json.loads(line) for line in result.stdout.splitlines() if line.strip()]
    assert len(responses) == 2 and "result" in responses[1], responses
    return json.loads(responses[1]["result"]["content"][0]["text"])


def assert_fts_lifecycle(project: Path) -> None:
    empty_root = project / "empty-root"
    empty_root.mkdir()
    empty_snapshot = {
        "snapshot": {"id": "empty"},
        "local_search_resources": [{"id": "empty", "package_id": "fixture", "kind": "knowledge", "content_roots": [str(empty_root)]}],
    }
    assert search(project, empty_snapshot, query="anything")["search_status"] == "missing"

    current_root = project / "current-root"
    current_root.mkdir()
    (current_root / "guide.md").write_text("Acceptance FTS lifecycle proof", encoding="utf-8")
    current_snapshot = {
        "snapshot": {"id": "current"},
        "local_search_resources": [{"id": "current", "package_id": "fixture", "kind": "knowledge", "content_roots": [str(current_root)]}],
    }
    # The existing empty index belongs to another snapshot, therefore the
    # first switch is intentionally stale and rebuilds before becoming fresh.
    assert search(project, current_snapshot, query="lifecycle")["search_status"] == "stale"
    assert search(project, current_snapshot, query="lifecycle")["search_status"] == "fresh"
    stale_snapshot = {**current_snapshot, "snapshot": {"id": "stale"}}
    assert search(project, stale_snapshot, query="lifecycle")["search_status"] == "stale"
    with patch("processforge_core.local_resource_search.sqlite3.connect", side_effect=sqlite3.OperationalError("fixture unavailable")):
        try:
            search(project, stale_snapshot, query="lifecycle")
        except LocalSearchError as exc:
            assert exc.code == "search_unavailable"
        else:
            raise AssertionError("unavailable SQLite index was accepted")


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="pf-project-init-acceptance-") as raw:
        root = Path(raw)
        workplace = root / "workplace"
        project = root / "project"
        cli("workplace-init", "--workplace", str(workplace), "--apply")
        cli("pack-activate", "--workplace", str(workplace), "--id", "processforge.official.software-development", "--apply")
        cli("specialization-create", "--workplace", str(workplace), "--id", "fixture-specialist", "--title", "Fixture specialist", "--apply")
        specialization_path = workplace / "specializations" / "specialization.fixture-specialist.yaml"
        specialization = yaml.safe_load(specialization_path.read_text(encoding="utf-8"))
        specialization["provides_capabilities"] = ["filesystem.read", "filesystem.write"]
        specialization["parameters"] = {"fixture_specialization_parameter": "enabled"}
        specialization_path.write_text(yaml.safe_dump(specialization, allow_unicode=True, sort_keys=False), encoding="utf-8")
        cli(
            "platform-create", "--workplace", str(workplace), "--id", "test-fixture", "--title", "Test fixture platform",
            "--project-type", "generic", "--process", "software-feature-development", "--apply",
        )
        platform_path = workplace / "platform-contracts" / "platform.test-fixture" / "platform-contract.yaml"
        platform = yaml.safe_load(platform_path.read_text(encoding="utf-8"))
        platform["requires"]["capabilities"] = []
        platform_path.write_text(yaml.safe_dump(platform, allow_unicode=True, sort_keys=False), encoding="utf-8")
        cli(
            "project-onboard", "--project-root", str(project), "--workplace", str(workplace), "--type", "generic",
            "--platform", "test-fixture", "--specialization", "fixture-specialist",
            "--process", "software-feature-development", "--apply",
        )
        manifest = yaml.safe_load((project / ".pf" / "process-forge.yaml").read_text(encoding="utf-8"))
        assert manifest["process"] == "software-feature-development"
        assert manifest["specializations"] == ["fixture-specialist"]
        assert any(item.get("id") == "platform.test-fixture" and item.get("platform") == "test-fixture" for item in manifest["platform_contracts"])
        snapshot_text = (project / ".pf" / "contexts" / "project-context.snapshot.yaml").read_text(encoding="utf-8")
        assert str(workplace) not in snapshot_text
        snapshot = yaml.safe_load(snapshot_text)
        parameter_sources = snapshot["parameter_resolution"]["sources"]
        specialization_source = next(item for item in parameter_sources if item["id"] == "specialization:specialization.fixture-specialist")
        assert specialization_source["path"] == "<private-source-ref>"
        status = json.loads(cli("project-init-status", "--project-root", str(project), "--workplace", str(workplace), "--json").stdout)
        assert status["state"] == "complete", status

        # Simulate a partial initialization: restore only a missing PF-owned
        # artifact and prove that a semantic user file stays untouched.
        start_here = project / ".pf" / "START_AGENT_HERE.md"
        start_here.unlink()
        semantic = project / ".pf" / "artifacts" / "user-semantic-note.md"
        semantic.write_text("preserve this user content", encoding="utf-8")
        repair_status = json.loads(cli("project-init-status", "--project-root", str(project), "--workplace", str(workplace), "--json").stdout)
        assert repair_status["state"] == "repairable"
        cli(
            "project-init-repair", "--project-root", str(project), "--workplace", str(workplace),
            "--repair-action", "restore_deterministic_artifacts", "--apply",
        )
        assert start_here.is_file()
        assert semantic.read_text(encoding="utf-8") == "preserve this user content"
        assert not list((project / ".pf").rglob("START_AGENT_HERE.md.candidate"))
        assert json.loads(cli("project-init-status", "--project-root", str(project), "--workplace", str(workplace), "--json").stdout)["state"] == "complete"

        assert_fts_lifecycle(project)

        print("STEP: verify session obligations", flush=True)
        cli("agent-checkin", "--workplace", str(workplace), "--agent", "fixture-agent", "--session", "fixture-session", "--project-root", str(project), "--role", "worker")
        print("STEP: create run", flush=True)
        cli("run-create", "--project-root", str(project), "--id", "fixture-run", "--title", "Fixture run", "--process", "software-feature-development", "--status", "in_progress", "--apply")
        print("STEP: start architecture", flush=True)
        cli("task-create", "--project-root", str(project), "--run", "fixture-run", "--id", "architecture-task", "--title", "Architecture task", "--process", "software-feature-development", "--stage", "architecture-plan", "--execution-mode", "planning_only", "--apply")
        cli("task-create", "--project-root", str(project), "--run", "fixture-run", "--id", "implementation-task", "--title", "Implementation task", "--process", "software-feature-development", "--stage", "implementation", "--execution-mode", "implementation", "--apply")
        cli("task-start", "--project-root", str(project), "--task", "architecture-task")
        cli("runtime-host", "rebuild-projections", "--project-root", str(project))
        print("STEP: read architecture context", flush=True)
        before = session_context_payload(workplace, core, session_id="fixture-session")
        assert before["work"]["stage_id"] == "architecture-plan"
        assert before["work"]["stage_obligations"]["freshness"] == "current"
        cli("task-complete", "--project-root", str(project), "--task", "architecture-task", "--summary", "fixture complete", "--apply")
        print("STEP: start implementation", flush=True)
        cli("task-start", "--project-root", str(project), "--task", "implementation-task")
        print("STEP: implementation task started", flush=True)
        print("STEP: read implementation context", flush=True)
        after = session_context_payload(workplace, core, session_id="fixture-session")
        assert after["work"]["stage_id"] == "implementation"
        assert after["work"]["stage_obligations"]["freshness"] == "current"
        assert before["work"]["stage_obligations"] != after["work"]["stage_obligations"]
    print("PASS: project initialization, repair, FTS5 lifecycle, and session obligation acceptance smoke")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
