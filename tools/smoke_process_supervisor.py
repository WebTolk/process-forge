#!/usr/bin/env python3
"""Smoke test for ProcessForge process supervisor MVP."""

from __future__ import annotations

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
    (project / "README.md").write_text("# Supervisor smoke\n", encoding="utf-8")
    pf("workplace-init", "--workplace", str(workplace), "--apply")
    pf("project-onboard", "--project-root", str(project), "--workplace", str(workplace), "--type", "generic-software-project", "--apply")
    return project


def write_plan(path: Path) -> None:
    path.write_text(
        """schema_version: 1
run:
  id: supervised-run
  title: Supervised run
  process: multi-agent-task-orchestration
orchestrator:
  role: orchestrator
runtime:
  default_driver: test-echo-worker
  supervisor_profile: default
  start_policy: supervisor
workers:
  - id: first-worker
    title: First worker
    role: test
    process: testing
    execution_mode: assurance
    writer: true
    allowed_files: [.pf/artifacts/**]
    allowed_read_files: [.pf/contexts/project-context.snapshot.yaml]
    forbidden_files: [tools/**]
    required_sources: [.pf/contexts/project-context.snapshot.yaml]
    required_outputs:
      - id: first-report
        path: .pf/artifacts/first-report.md
        type: markdown
        required: true
    expected_report_artifact: .pf/artifacts/first-report.md
    runtime_driver: test-echo-worker
    worker_may_rebuild_context: false
  - id: second-worker
    title: Second worker
    role: test
    process: testing
    execution_mode: assurance
    writer: true
    allowed_files: [.pf/artifacts/**]
    allowed_read_files: [.pf/contexts/project-context.snapshot.yaml]
    forbidden_files: [tools/**]
    required_sources: [.pf/contexts/project-context.snapshot.yaml]
    required_outputs:
      - id: second-report
        path: .pf/artifacts/second-report.md
        type: markdown
        required: true
    expected_report_artifact: .pf/artifacts/second-report.md
    runtime_driver: test-echo-worker
    depends_on: [first-worker]
    worker_may_rebuild_context: false
integration:
  required: true
  role: orchestrator
  expected_output: .pf/artifacts/integration-report.md
""",
        encoding="utf-8",
    )


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="pf-supervisor-") as temp:
        root = Path(temp)
        project = make_project(root)
        plan = root / "plan.yaml"
        write_plan(plan)
        pf("orchestrator-plan", "validate", "--project-root", str(project), "--plan", str(plan))
        pf("orchestrator-plan", "apply", "--project-root", str(project), "--plan", str(plan), "--apply")
        pf("supervisor", "run", "--project-root", str(project), "--run", "supervised-run", "--max-ticks", "2", "--interval", "0")
        status = pf("run-status", "--project-root", str(project), "--run", "supervised-run").stdout
        if "TASKS: done=2" not in status:
            raise AssertionError("supervisor did not complete both tasks")
        for rel_path in [
            ".pf/runtime/supervisor/state.json",
            ".pf/runtime/supervisor/last-tick-report.md",
            ".pf/runtime/agent-runs/supervised-run/first-worker/status.json",
            ".pf/runtime/agent-runs/supervised-run/second-worker/status.json",
            ".pf/artifacts/first-report.md",
            ".pf/artifacts/second-report.md",
        ]:
            if not (project / rel_path).is_file():
                raise AssertionError(f"missing supervisor file: {rel_path}")
    print("PASS: process supervisor smoke")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
