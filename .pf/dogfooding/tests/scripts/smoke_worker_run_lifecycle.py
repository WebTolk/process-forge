#!/usr/bin/env python3
"""Smoke test for ProcessForge worker-run lifecycle MVP."""

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


def pf(*args: str, expect: int = 0, timeout: int = 90) -> CommandResult:
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
    (project / "README.md").write_text("# Worker run smoke\n", encoding="utf-8")
    pf("workplace-init", "--workplace", str(workplace), "--apply")
    pf("project-onboard", "--project-root", str(project), "--workplace", str(workplace), "--type", "generic-software-project", "--apply")
    return project


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="pf-worker-run-") as temp:
        project = make_project(Path(temp))
        pf("run-create", "--project-root", str(project), "--id", "echo-run", "--title", "Echo run", "--process", "task-batch-execution", "--apply")
        pf(
            "task-create",
            "--project-root",
            str(project),
            "--run",
            "echo-run",
            "--id",
            "echo-task",
            "--title",
            "Echo task",
            "--process",
            "testing",
            "--allowed-file",
            ".pf/artifacts/**",
            "--required-output",
            "id=echo-report,path=.pf/artifacts/echo-report.md,type=markdown,required=true",
            "--expected-report-artifact",
            ".pf/artifacts/echo-report.md",
            "--apply",
        )
        pf("worker-run", "prepare", "--project-root", str(project), "--task", "echo-task", "--driver", "test-echo-worker")
        pf("worker-run", "start", "--project-root", str(project), "--task", "echo-task", "--driver", "test-echo-worker")
        pf("worker-run", "collect", "--project-root", str(project), "--task", "echo-task")
        status = pf("worker-run", "status", "--project-root", str(project), "--task", "echo-task").stdout
        if "status: completed" not in status:
            raise AssertionError("worker-run status did not report completed")
        for rel_path in [
            ".pf/runtime/agent-runs/echo-run/echo-task/status.json",
            ".pf/runtime/agent-runs/echo-run/echo-task/command.json",
            ".pf/runtime/agent-runs/echo-run/echo-task/process.json",
            ".pf/runtime/agent-runs/echo-run/echo-task/exit.json",
            ".pf/runtime/agent-runs/echo-run/echo-task/heartbeat.json",
            ".pf/artifacts/echo-report.md",
        ]:
            if not (project / rel_path).is_file():
                raise AssertionError(f"missing worker-run file: {rel_path}")
    print("PASS: worker-run lifecycle smoke")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
