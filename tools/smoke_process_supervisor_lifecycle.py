#!/usr/bin/env python3
"""Smoke test for supervisor run lifecycle with shell-launched workers."""

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


def make_project(root: Path) -> Path:
    workplace = root / "workplace"
    project = root / "project"
    project.mkdir()
    (project / "README.md").write_text("# Supervisor lifecycle smoke\n", encoding="utf-8")
    pf("workplace-init", "--workplace", str(workplace), "--apply")
    pf("project-onboard", "--project-root", str(project), "--workplace", str(workplace), "--type", "generic-software-project", "--apply")
    return project


def write_plan(path: Path) -> None:
    path.write_text(
        """schema_version: 1
run:
  id: shell-supervisor-run
  title: Shell supervisor run
  process: multi-agent-task-orchestration
orchestrator:
  role: orchestrator
runtime:
  default_driver: test-shell-agent
  supervisor_profile: default
  start_policy: supervisor
workers:
  - id: shell-agent
    title: Shell agent
    role: test
    process: testing
    execution_mode: assurance
    writer: true
    allowed_files: [.pf/artifacts/**]
    allowed_read_files: [.pf/contexts/project-context.snapshot.yaml]
    required_sources: [.pf/contexts/project-context.snapshot.yaml]
    required_outputs:
      - id: shell-agent-report
        path: .pf/artifacts/shell-agent-report.md
        type: markdown
        required: true
    expected_report_artifact: .pf/artifacts/shell-agent-report.md
    runtime_driver: test-shell-agent
    worker_may_rebuild_context: false
integration:
  required: false
  role: orchestrator
  expected_output: .pf/artifacts/integration-report.md
""",
        encoding="utf-8",
    )


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="pf-supervisor-lifecycle-") as temp:
        root = Path(temp)
        project = make_project(root)
        plan = root / "plan.yaml"
        write_plan(plan)
        pf("orchestrator-plan", "validate", "--project-root", str(project), "--plan", str(plan))
        pf("orchestrator-plan", "apply", "--project-root", str(project), "--plan", str(plan), "--apply")
        pf("supervisor", "run", "--project-root", str(project), "--run", "shell-supervisor-run", "--max-ticks", "6", "--interval", "0")
        status = pf("run-status", "--project-root", str(project), "--run", "shell-supervisor-run").stdout
        if "TASKS: done=1" not in status:
            raise AssertionError("supervisor lifecycle did not complete shell-agent task")
        process = json.loads((project / ".pf/runtime/agent-runs/shell-supervisor-run/shell-agent/process.json").read_text(encoding="utf-8"))
        if not isinstance(process.get("pid"), int) or process["pid"] <= 0:
            raise AssertionError("process proof does not contain a valid pid")
        if not (project / ".pf/runtime/agent-runs/shell-supervisor-run/shell-agent/stdout.log").read_text(encoding="utf-8").strip():
            raise AssertionError("shell-agent stdout proof is empty")
    print("PASS: process supervisor lifecycle smoke")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
