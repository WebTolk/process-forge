"""Source initialization/repair entry acceptance in isolated Windows/POSIX fixtures.

The stdio probe proves the source MCP adapter, not the connected application host.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from unittest.mock import patch

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
import processforge as core
from processforge_core.project import initialization
from processforge_core.agent_entry import migration
from processforge_core.agent_entry.contract import BOM, block_span, load_contract


LEGACY_PREFIX = """# ProcessForge Project Instructions

This project uses ProcessForge.

## Start Order

1. Read `.pf/START_AGENT_HERE.md` and `.pf/process-forge.yaml`.
2. Call `pf.context` with this project root. If MCP is unavailable, read the
   current snapshot as the file-only fallback.
3. Use `pf.search` when project, platform, process, template, or tool knowledge
   is needed.
4. Use `pf.resolve` before opening a ProcessForge-managed resource root.
5. Call `pf.work.start` with the high-level objective when work becomes
   substantive, then follow the selected assignment and capsule.
6. Write durable artifacts, reviews, logs, and handoffs required by the work.

"""


def tree(root: Path) -> dict:
    return {p.relative_to(root).as_posix(): (p.read_bytes(), p.stat().st_mtime_ns)
            for p in root.rglob("*") if p.is_file()}


def assert_tree(root: Path, before: dict):
    after = tree(root)
    changes = sorted(name for name in before.keys() | after.keys() if before.get(name) != after.get(name))
    assert not changes, changes


def cli(*args: str, succeeds: bool = True):
    result = subprocess.run([sys.executable, "-B", str(ROOT / "tools/processforge.py"), *args],
                            cwd=ROOT, capture_output=True, text=True, encoding="utf-8", timeout=90)
    assert (result.returncode == 0) == succeeds, result.stdout + result.stderr
    if succeeds and args[0] in {"project-init", "project-init-repair", "project-init-status"}:
        return yaml.safe_load(result.stdout)
    return result.stdout + result.stderr


def budget(limit: int):
    return [{"id": "observed", "unit": "utf8_bytes", "scope": "chain", "selection": ["AGENTS.md"],
             "limit": limit, "overflow": "truncate", "source": "explicit", "accounting_phase": "raw_concat"}]


def onboard(project: Path, workplace: Path, *extra: str, succeeds=True):
    return cli("project-init", "--project-root", str(project), "--workplace", str(workplace), *extra, succeeds=succeeds)


def repair(project: Path, workplace: Path, action="migrate_agent_entry", *extra: str, succeeds=True):
    return cli("project-init-repair", "--project-root", str(project), "--workplace", str(workplace),
               "--repair-action", action, *extra, succeeds=succeeds)


def status(project: Path, workplace: Path):
    return cli("project-init-status", "--project-root", str(project), "--workplace", str(workplace), "--json")


def assert_contract(project: Path, contract):
    for name in migration.TARGETS[:2]:
        raw = (project / name).read_bytes()
        start, end = block_span(raw, contract)
        assert raw[start:end].replace(b"\r\n", b"\n") == contract.raw


def mcp(workplace: Path, name: str, arguments: dict):
    requests = [{"jsonrpc": "2.0", "id": 1, "method": "initialize"},
                {"jsonrpc": "2.0", "id": 2, "method": "tools/call", "params": {"name": name, "arguments": arguments}}]
    result = subprocess.run([sys.executable, "-B", str(ROOT / "tools/pf_runtime/mcp_server.py"),
                             "--workplace", str(workplace), "--session", "entry-fixture-session"],
                            cwd=ROOT, input="\n".join(json.dumps(row) for row in requests) + "\n",
                            capture_output=True, text=True, encoding="utf-8", timeout=90)
    assert result.returncode == 0, result.stderr
    response = json.loads(result.stdout.splitlines()[-1])
    assert "result" in response, response
    return json.loads(response["result"]["content"][0]["text"])


def main():
    contract = load_contract()
    with tempfile.TemporaryDirectory(prefix="pf-init-entry-") as temporary:
        base = Path(temporary)
        workplace, project = base / "workplace", base / "project"
        cli("workplace-init", "--profile", "generic", "--workplace", str(workplace), "--apply")
        project.mkdir()
        user = BOM + "# User rules\r\nPreserve 😀".encode("utf-8")
        (project / "AGENTS.md").write_bytes(user)
        before = tree(project)
        planned = onboard(project, workplace)
        assert not planned["applied"] and planned["agent_entry"]["status"] == "planned", planned
        assert set(migration.TARGETS).issubset(planned["planned_artifacts"])
        assert ".pf/START_AGENT_HERE.md" not in planned["planned_artifacts"]
        assert_tree(project, before)
        applied = onboard(project, workplace, "--apply")
        assert applied["status"] == "complete" and applied["agent_entry"]["action"] == "applied", applied
        assert (project / "AGENTS.md").read_bytes().startswith(user + b"\n\n")
        assert_contract(project, contract)
        assert not (project / ".codex/hooks.json").exists()
        assert not (project / ".pf/START_AGENT_HERE.md").exists()
        stable = {name: tree(project)[name] for name in migration.TARGETS}
        repeated = onboard(project, workplace, "--apply")
        assert repeated["agent_entry"]["action"] == "unchanged", repeated
        assert {name: tree(project)[name] for name in stable} == stable
        before = tree(project)
        observed = status(project, workplace)
        assert observed["state"] == "complete" and observed["agent_entry"]["status"] == "current", observed
        assert observed["agent_entry"]["budget"]["status"] == "budget_unverified"
        assert_tree(project, before)
        assert repair(project, workplace, "migrate_agent_entry", "--apply")["result"]["agent_entry"]["action"] == "unchanged"
        assert_tree(project, before)

        # Missing START is normal, including repeated/forced init and deterministic repair.
        onboard(project, workplace, "--apply", "--force")
        repair(project, workplace, "restore_deterministic_artifacts", "--apply")
        assert not (project / ".pf/START_AGENT_HERE.md").exists()
        assert status(project, workplace)["state"] == "complete"
        cli("doctor-project", "--project-root", str(project))

        # Recognized legacy prefix with custom BOM/CRLF suffix. Entry absence is
        # independent of a fresh context, and explicit migration preserves pins.
        legacy = base / "legacy"
        onboard(legacy, workplace, "--apply")
        (legacy / "AGENTS.md").unlink()
        (legacy / ".pf/agent-entry.json").unlink()
        suffix = b"## Important Rules\r\n\r\nCustom extended bytes\r\n"
        (legacy / ".pf/AGENTS.md").write_bytes(BOM + LEGACY_PREFIX.encode().replace(b"\n", b"\r\n") + suffix)
        start = legacy / ".pf/START_AGENT_HERE.md"
        start.write_bytes(BOM + b"# Operator START\r\nKeep exactly\r\n")
        snapshot = legacy / ".pf/contexts/project-context.snapshot.yaml"
        snapshot_before = snapshot.read_bytes()
        before = tree(legacy)
        observed = status(legacy, workplace)
        assert observed["state"] == "complete" and observed["snapshot"]["status"] == "fresh", observed
        assert observed["agent_entry"]["entry"] == "legacy_or_unmigrated", observed
        assert "migrate_agent_entry" in observed["repair_plan"]
        repair(legacy, workplace)
        assert tree(legacy) == before
        migrated = repair(legacy, workplace, "migrate_agent_entry", "--apply")
        assert migrated["result"]["status"] == "complete", migrated
        assert (legacy / ".pf/AGENTS.md").read_bytes() == BOM + contract.raw + b"\n" + suffix
        assert snapshot.read_bytes() == snapshot_before
        assert tree(legacy)[".pf/START_AGENT_HERE.md"] == before[".pf/START_AGENT_HERE.md"]
        onboard(legacy, workplace, "--apply", "--force")
        assert tree(legacy)[".pf/START_AGENT_HERE.md"] == before[".pf/START_AGENT_HERE.md"]

        repair(legacy, workplace, "restore_deterministic_artifacts", "--apply")
        assert tree(legacy)[".pf/START_AGENT_HERE.md"] == before[".pf/START_AGENT_HERE.md"]

        # Refusal must precede all normal init writes, including --force and repair.
        (legacy / ".pf/AGENTS.md").write_bytes(b"# Unrecognized operator instructions\n")
        before = tree(legacy)
        assert "legacy_hidden_unknown" in onboard(legacy, workplace, "--apply", "--force", succeeds=False)
        assert "legacy_hidden_unknown" in repair(legacy, workplace, "restore_deterministic_artifacts", "--apply", succeeds=False)
        assert tree(legacy) == before
        observed = status(legacy, workplace)
        assert observed["agent_entry"]["status"] == "conflict"
        assert observed["state"] == "complete", observed
        assert tree(legacy) == before

        bounded = base / "bounded"
        bounded.mkdir()
        (bounded / "AGENTS.md").write_bytes(b"u" * 30720)
        policy = base / "observed-budget.json"
        policy.write_text(json.dumps(budget(32768)), encoding="utf-8")
        before = tree(bounded)
        refusal = onboard(bounded, workplace, "--apply", "--force", "--entry-budget-file", str(policy), succeeds=False)
        assert "entry_contract_would_truncate" in refusal, refusal
        assert tree(bounded) == before and not (bounded / ".pf").exists()

        interrupted = base / "interrupted"
        interrupted.mkdir()
        real_apply = migration.apply_entry
        def fail_after_root(point, _transaction):
            if point == "replaced:AGENTS.md":
                raise OSError("fixture interruption")
        def interrupted_apply(*args, **kwargs):
            return real_apply(*args, **kwargs, _fault=fail_after_root)
        with patch.object(migration, "apply_entry", interrupted_apply):
            failed = initialization.initialize_project({"project_root": str(interrupted), "workplace": str(workplace), "apply": True}, core)
        assert failed["result"]["status"] == "blocked", failed
        receipt = failed["result"]["agent_entry"]
        assert receipt["action"] == "incomplete" and receipt["transaction"]
        assert not (interrupted / ".pf/process-forge.yaml").exists()
        assert not (interrupted / ".pf/runtime/events/events.ndjson").exists()
        migration.rollback_entry(interrupted, receipt["transaction"], apply=True)

        if os.name == "nt":
            link, target = base / "redirected", base / "outside"
            target.mkdir()
            created = subprocess.run(["cmd", "/c", "mklink", "/J", str(link), str(target)], capture_output=True)
            assert created.returncode == 0, created.stderr
            try:
                before = tree(target)
                assert "unsupported_path" in onboard(link, workplace, "--apply", succeeds=False)
                assert tree(target) == before
            finally:
                assert link.parent == base and link.lstat().st_file_attributes & 0x400
                os.rmdir(link)

        # Source stdio MCP uses the same service and retains exact apply/session gates.
        cli("agent-checkin", "--workplace", str(workplace), "--agent", "entry-fixture-agent",
            "--session", "entry-fixture-session", "--project-root", str(project), "--role", "worker")
        initialized = mcp(workplace, "pf.project_initialization.initialize", {"apply": True})
        assert initialized["result"]["agent_entry"]["action"] == "unchanged", initialized
        assert not (project / ".pf/START_AGENT_HERE.md").exists()
        before = tree(project)
        refused = mcp(workplace, "pf.project_initialization.initialize", {"apply": True, "force": True, "entry_budget_policy": budget(0)})
        assert refused["error"]["code"] == "entry_contract_would_truncate", refused
        assert_tree(project, before)
        refused = mcp(workplace, "pf.project_initialization.repair", {"apply": True, "repair_action": "migrate_agent_entry", "entry_budget_policy": budget(0)})
        assert refused["error"]["code"] == "entry_contract_would_truncate", refused
        assert_tree(project, before)
        denied = mcp(workplace, "pf.project_initialization.repair", {"repair_action": "migrate_agent_entry"})
        assert denied["error"]["code"] == "apply_required", denied
        assert_tree(project, before)
        observed = mcp(workplace, "pf.project_initialization.status", {})
        assert observed["agent_entry"]["status"] == "current", observed
        assert observed["state"] == "complete", observed
        assert_tree(project, before)
        migrated = mcp(workplace, "pf.project_initialization.repair", {"apply": True, "repair_action": "migrate_agent_entry"})
        assert migrated["result"]["agent_entry"]["action"] == "unchanged", migrated
        assert_tree(project, before)
    print("PASS: init/repair shared entry, legacy status, user bytes/START/pins, no-write refusals, budgets, interruption and source stdio MCP")


if __name__ == "__main__":
    main()
