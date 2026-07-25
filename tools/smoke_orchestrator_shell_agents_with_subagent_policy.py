#!/usr/bin/env python3
"""Smoke test for orchestrator shell agents and subagent report policy."""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

from processforge_subprocess import CommandResult, diagnostic_text, run_command as run_processforge_command


ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "tools" / "processforge.py"
PLAN = ROOT / "examples" / "orchestrator-shell-agents" / "minimal" / "orchestrator-shell-agent-plan.yaml"


def pf(*args: str, expect: int = 0, timeout: int = 120) -> CommandResult:
    result = run_processforge_command([sys.executable, str(CLI), *args], cwd=ROOT, timeout=timeout)
    if result.timed_out:
        raise AssertionError("timeout: " + " ".join(args) + "\n" + diagnostic_text(result))
    if result.returncode != expect:
        raise AssertionError(f"expected {expect}, got {result.returncode}: {' '.join(args)}\n{diagnostic_text(result)}")
    return result


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="pf-orch-shell-") as temp:
        root = Path(temp)
        workplace = root / "workplace"
        project = root / "project"
        project.mkdir()
        (project / "README.md").write_text("# Orchestrator shell smoke\n", encoding="utf-8")
        pf("workplace-init", "--workplace", str(workplace), "--apply")
        pf("project-onboard", "--project-root", str(project), "--workplace", str(workplace), "--type", "generic-software-project", "--apply")
        pf("orchestrator-shell-plan-create", "--project-root", str(project), "--run", "orchestrated-work", "--title", "Orchestrated work", "--answers", str(PLAN), "--apply")
        pf("orchestrator-shell-plan-validate", "--project-root", str(project), "--run", "orchestrated-work")
        pf("orchestrator-shell-plan-apply", "--project-root", str(project), "--run", "orchestrated-work", "--workplace", str(workplace), "--apply", timeout=180)
        docs_report = project / ".pf" / "artifacts" / "docs-shell-agent-report.md"
        test_report = project / ".pf" / "artifacts" / "test-shell-agent-report.md"
        subagent_dir = project / ".pf" / "artifacts" / "subagents" / "docs-shell-agent"
        if not docs_report.is_file() or not test_report.is_file():
            raise AssertionError("required shell-agent reports missing")
        if "simulated_subagents: `true`" not in docs_report.read_text(encoding="utf-8"):
            raise AssertionError("subagent-enabled worker did not declare simulated subagent usage")
        if "simulated_subagents: `false`" not in test_report.read_text(encoding="utf-8"):
            raise AssertionError("subagent-disabled worker reported subagent usage")
        if len(list(subagent_dir.glob("*.md"))) != 2:
            raise AssertionError("required subagent reports were not written")
        leases = list((workplace / "runtime" / "agent-leases").glob("lease-orchestrated-work-*.yaml"))
        if len(leases) != 2:
            raise AssertionError("shell workers did not receive leases")
    print("PASS: orchestrator shell agents with subagent policy smoke")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
