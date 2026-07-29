#!/usr/bin/env python3
"""Smoke test for supervisor tick failure propagation."""

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
    (project / "README.md").write_text("# Supervisor tick smoke\n", encoding="utf-8")
    pf("workplace-init", "--workplace", str(workplace), "--apply")
    pf("project-onboard", "--project-root", str(project), "--workplace", str(workplace), "--type", "generic-software-project", "--apply")
    return project


def write_plan(path: Path, driver: str) -> None:
    path.write_text(
        f"""schema_version: 1
run:
  id: tick-run
  title: Tick run
  process: multi-agent-task-orchestration
orchestrator:
  role: orchestrator
runtime:
  default_driver: {driver}
  supervisor_profile: default
  start_policy: supervisor
workers:
  - id: failing-worker
    title: Failing worker
    role: test
    process: task-batch-execution
    execution_mode: assurance
    writer: true
    allowed_files: [.pf/artifacts/**]
    allowed_read_files: [.pf/contexts/project-context.snapshot.yaml]
    required_sources: [.pf/contexts/project-context.snapshot.yaml]
    required_outputs:
      - id: failing-report
        path: .pf/artifacts/failing-report.md
        type: markdown
        required: true
    expected_report_artifact: .pf/artifacts/failing-report.md
    runtime_driver: {driver}
    worker_may_rebuild_context: false
integration:
  required: false
  role: orchestrator
  expected_output: .pf/artifacts/integration-report.md
""",
        encoding="utf-8",
    )


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="pf-supervisor-tick-") as temp:
        root = Path(temp)
        project = make_project(root)
        plan = root / "plan.yaml"
        write_plan(plan, "generic-shell")
        pf("orchestrator-plan", "validate", "--project-root", str(project), "--plan", str(plan))
        pf("orchestrator-plan", "apply", "--project-root", str(project), "--plan", str(plan), "--apply")
        result = pf("supervisor", "tick", "--project-root", str(project), "--run", "tick-run", expect=1)
        if "failed=1" not in result.stdout:
            raise AssertionError("supervisor tick did not report one failed worker")
        report = project / ".pf/runtime/supervisor/last-tick-report.md"
        if "- failed: `failing-worker`" not in report.read_text(encoding="utf-8"):
            raise AssertionError("supervisor tick report missing failed worker")
    print("PASS: process supervisor tick smoke")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
