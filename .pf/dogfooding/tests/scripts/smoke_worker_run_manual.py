#!/usr/bin/env python3
"""Smoke test for manual worker-run preparation."""

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
    (project / "README.md").write_text("# Manual worker smoke\n", encoding="utf-8")
    pf("workplace-init", "--workplace", str(workplace), "--apply")
    pf("project-onboard", "--project-root", str(project), "--workplace", str(workplace), "--type", "generic-software-project", "--apply")
    return project


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="pf-worker-manual-") as temp:
        project = make_project(Path(temp))
        pf("run-create", "--project-root", str(project), "--id", "manual-run", "--title", "Manual run", "--process", "task-batch-execution", "--apply")
        pf(
            "task-create",
            "--project-root",
            str(project),
            "--run",
            "manual-run",
            "--id",
            "manual-task",
            "--title",
            "Manual task",
            "--process",
            "testing",
            "--allowed-file",
            ".pf/artifacts/**",
            "--expected-report-artifact",
            ".pf/artifacts/manual-report.md",
            "--apply",
        )
        pf("worker-run", "prepare", "--project-root", str(project), "--task", "manual-task", "--driver", "manual")
        pf("worker-run", "start", "--project-root", str(project), "--task", "manual-task", "--driver", "manual")
        status = pf("worker-run", "status", "--project-root", str(project), "--task", "manual-task").stdout
        if "status: manual_required" not in status:
            raise AssertionError("manual worker did not remain manual_required")
        if (project / ".pf/runtime/agent-runs/manual-run/manual-task/process.json").exists():
            raise AssertionError("manual worker unexpectedly wrote process.json")
    print("PASS: worker-run manual smoke")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
