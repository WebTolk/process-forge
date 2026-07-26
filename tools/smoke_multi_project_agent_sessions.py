#!/usr/bin/env python3
"""Smoke test for multiple active sessions with the same agent id."""

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


def session_rows(stdout: str) -> list[dict[str, object]]:
    data = json.loads(stdout)
    if isinstance(data, list):
        return [item for item in data if isinstance(item, dict)]
    if isinstance(data, dict):
        return [data]
    return []


def statuses(rows: list[dict[str, object]]) -> dict[str, str]:
    return {str(item.get("session_id")): str(item.get("status")) for item in rows}


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="pf-multi-project-sessions-") as temp:
        root = Path(temp)
        workplace = root / "workplace"
        project_a = root / "project-a"
        project_b = root / "project-b"
        project_a.mkdir()
        project_b.mkdir()
        (project_a / "README.md").write_text("# Project A\n", encoding="utf-8")
        (project_b / "README.md").write_text("# Project B\n", encoding="utf-8")

        pf("workplace-init", "--workplace", str(workplace), "--apply")
        pf("project-onboard", "--project-root", str(project_a), "--workplace", str(workplace), "--type", "generic-software-project", "--apply")
        pf("project-onboard", "--project-root", str(project_b), "--workplace", str(workplace), "--type", "generic-software-project", "--apply")
        pf("session-start", "--workplace", str(workplace), "--project-root", str(project_a), "--agent", "primary-agent", "--session", "sess-a", "--process", "task-batch-execution", "--role", "primary-agent")
        pf("session-start", "--workplace", str(workplace), "--project-root", str(project_b), "--agent", "primary-agent", "--session", "sess-b", "--process", "task-batch-execution", "--role", "primary-agent")

        all_rows = session_rows(pf("agent-status", "--workplace", str(workplace), "--agent", "primary-agent", "--json").stdout)
        all_statuses = statuses(all_rows)
        if all_statuses.get("sess-a") != "online" or all_statuses.get("sess-b") != "online":
            raise AssertionError(f"same agent_id should have two active sessions, got {all_statuses}")
        project_a_rows = session_rows(pf("agent-status", "--project-root", str(project_a), "--json").stdout)
        project_b_rows = session_rows(pf("session-status", "--project-root", str(project_b), "--json").stdout)
        if statuses(project_a_rows) != {"sess-a": "online"}:
            raise AssertionError(f"project A status should only show sess-a, got {project_a_rows}")
        if statuses(project_b_rows) != {"sess-b": "online"}:
            raise AssertionError(f"project B status should only show sess-b, got {project_b_rows}")

        pf("agent-checkout", "--project-root", str(project_a))
        after_a_checkout = statuses(session_rows(pf("agent-status", "--workplace", str(workplace), "--agent", "primary-agent", "--json").stdout))
        if after_a_checkout.get("sess-a") != "checked_out" or after_a_checkout.get("sess-b") != "online":
            raise AssertionError(f"checkout of project A should not affect project B, got {after_a_checkout}")
        pf("session-end", "--project-root", str(project_b))
        after_b_checkout = statuses(session_rows(pf("agent-status", "--workplace", str(workplace), "--agent", "primary-agent", "--json").stdout))
        if after_b_checkout.get("sess-b") != "checked_out":
            raise AssertionError(f"session-end did not checkout project B, got {after_b_checkout}")

    print("PASS: multi-project agent sessions smoke")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
