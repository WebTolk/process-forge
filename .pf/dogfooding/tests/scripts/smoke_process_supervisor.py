#!/usr/bin/env python3
"""Smoke test for ProcessForge process supervisor MVP."""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(os.environ.get("PF_REPO_ROOT", Path(__file__).resolve().parents[4])).resolve()
TOOLS_DIR = ROOT / "tools"
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

from processforge_subprocess import CommandResult, diagnostic_text, run_command as run_processforge_command

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


def run_status(project: Path) -> str:
    return pf("run-status", "--project-root", str(project), "--run", "supervised-run").stdout


def wait_for_done(project: Path, expected_done: int, attempts: int = 8) -> str:
    last_status = ""
    for _index in range(attempts):
        pf("supervisor", "run", "--project-root", str(project), "--run", "supervised-run", "--max-ticks", "2", "--interval", "0.05")
        last_status = run_status(project)
        if f"done={expected_done}" in last_status:
            return last_status
    raise AssertionError(f"supervisor did not reach done={expected_done}\n{last_status}")


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="pf-supervisor-") as temp:
        root = Path(temp)
        project = make_project(root)
        plan = root / "plan.yaml"
        write_plan(plan)
        pf("orchestrator-plan", "validate", "--project-root", str(project), "--plan", str(plan))
        pf("orchestrator-plan", "apply", "--project-root", str(project), "--plan", str(plan), "--apply")
        pf("supervisor", "run", "--project-root", str(project), "--run", "supervised-run", "--max-ticks", "1", "--interval", "0", "--final-drain-timeout", "3")
        first_status = run_status(project)
        if "done=1" not in first_status or "open=1" not in first_status:
            raise AssertionError("final drain should collect the first task without starting the dependent task\n" + first_status)
        second_runtime = project / ".pf/runtime/agent-runs/supervised-run/second-worker/status.json"
        if second_runtime.is_file():
            raise AssertionError("final drain started dependent second-worker")
        status = wait_for_done(project, 2)
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
