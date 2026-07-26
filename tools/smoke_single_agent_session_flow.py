#!/usr/bin/env python3
"""Smoke test for the default single-agent ProcessForge session flow."""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

from processforge_subprocess import CommandResult, diagnostic_text, run_command as run_processforge_command


ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "tools" / "processforge.py"


def pf(*args: str, expect: int = 0, timeout: int = 120) -> CommandResult:
    result = run_processforge_command([sys.executable, str(CLI), *args], cwd=ROOT, timeout=timeout)
    if result.timed_out:
        raise AssertionError("timeout: " + " ".join(args) + "\n" + diagnostic_text(result))
    if result.returncode != expect:
        raise AssertionError(f"expected {expect}, got {result.returncode}: {' '.join(args)}\n{diagnostic_text(result)}")
    return result


def read_json(path: Path) -> dict[str, object]:
    data = json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}
    return data if isinstance(data, dict) else {}


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="pf-single-agent-session-") as temp:
        root = Path(temp)
        workplace = root / "workplace"
        project = root / "project"
        project.mkdir()
        (project / "README.md").write_text("# Single agent session smoke\n", encoding="utf-8")

        pf("workplace-init", "--workplace", str(workplace), "--apply")
        pf("project-onboard", "--project-root", str(project), "--workplace", str(workplace), "--type", "generic-software-project", "--apply")
        checkin = json.loads(
            pf(
                "session-start",
                "--workplace",
                str(workplace),
                "--project-root",
                str(project),
                "--agent",
                "primary-agent",
                "--process",
                "task-batch-execution",
                "--role",
                "primary-agent",
                "--json",
            ).stdout
        )
        session_id = str(checkin.get("session_id") or "")
        if not session_id.startswith("sess-primary-agent-"):
            raise AssertionError(f"session-start did not return generated session id: {session_id}")
        presence = workplace / "runtime" / "agent-presence" / "primary-agent" / f"{session_id}.json"
        if not presence.is_file():
            raise AssertionError("session-safe presence file missing")
        if read_json(project / ".pf" / "runtime" / "current-session.json").get("session_id") != session_id:
            raise AssertionError("project current-session reference missing")
        if "agent.checked_in" not in (workplace / "runtime" / "agent-ledger" / "sessions.ndjson").read_text(encoding="utf-8"):
            raise AssertionError("ledger check-in event missing")

        run_id = "single-agent-run"
        pf("run-create", "--project-root", str(project), "--id", run_id, "--title", "Single agent run", "--process", "task-batch-execution", "--apply")
        pf("task-create", "--project-root", str(project), "--run", run_id, "--id", "single-task", "--title", "Single task", "--process", "testing", "--owner", "primary-agent", "--role", "primary-agent", "--apply")
        pf("iteration-add", "--project-root", str(project), "--task", "single-task", "--kind", "work", "--summary", "Primary agent performed the work.", "--apply")
        pf("task-complete", "--project-root", str(project), "--task", "single-task", "--summary", "Primary agent completed the task.", "--apply")
        pf("run-summary", "--project-root", str(project), "--run", run_id, "--apply")
        pf("run-complete", "--project-root", str(project), "--run", run_id, "--apply")
        pf("run-doctor", "--project-root", str(project), "--run", run_id)
        pf("task-doctor", "--project-root", str(project), "--task", "single-task")
        pf("agent-checkout", "--project-root", str(project))

        current = read_json(project / ".pf" / "runtime" / "current-session.json")
        if current.get("status") != "checked_out" or current.get("session_id") != session_id:
            raise AssertionError("project current-session was not checked out")
        ledger_text = (workplace / "runtime" / "agent-ledger" / "sessions.ndjson").read_text(encoding="utf-8")
        if "agent.checked_out" not in ledger_text:
            raise AssertionError("ledger checkout event missing")
        agent_runs = project / ".pf" / "runtime" / "agent-runs"
        if agent_runs.exists() and any(agent_runs.rglob("*")):
            raise AssertionError("single-agent flow should not require supervisor/runtime worker state")
        if any((workplace / "runtime" / "agent-leases").glob("*.yaml")):
            raise AssertionError("single-agent flow should not require explicit leases")
        if (project / ".pf" / "handoffs").joinpath("handoff-feature").exists():
            raise AssertionError("single-agent flow unexpectedly invoked director handoff flow")

    print("PASS: single-agent session flow smoke")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
