#!/usr/bin/env python3
"""Smoke test for shell worker-run launch and environment isolation."""

from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path

from processforge_subprocess import CommandResult, diagnostic_text, run_command as run_processforge_command


ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "tools" / "processforge.py"


def pf(*args: str, expect: int = 0, timeout: int = 90) -> CommandResult:
    env = os.environ.copy()
    env["PF_LEAK_TEST_SECRET"] = "must-not-reach-worker"
    result = run_processforge_command([sys.executable, str(CLI), *args], cwd=ROOT, timeout=timeout, env=env)
    if result.timed_out:
        raise AssertionError("timeout: " + " ".join(args) + "\n" + diagnostic_text(result))
    if result.returncode != expect:
        raise AssertionError(f"expected {expect}, got {result.returncode}: {' '.join(args)}\n{diagnostic_text(result)}")
    return result


def make_project(root: Path) -> Path:
    workplace = root / "workplace"
    project = root / "project"
    project.mkdir()
    (project / "README.md").write_text("# Shell worker smoke\n", encoding="utf-8")
    pf("workplace-init", "--workplace", str(workplace), "--apply")
    pf("project-onboard", "--project-root", str(project), "--workplace", str(workplace), "--type", "generic-software-project", "--apply")
    return project


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="pf-worker-shell-") as temp:
        project = make_project(Path(temp))
        pf("run-create", "--project-root", str(project), "--id", "shell-run", "--title", "Shell run", "--process", "task-batch-execution", "--apply")
        pf(
            "task-create",
            "--project-root",
            str(project),
            "--run",
            "shell-run",
            "--id",
            "shell-task",
            "--title",
            "Shell task",
            "--process",
            "testing",
            "--allowed-file",
            ".pf/artifacts/**",
            "--required-output",
            "id=shell-report,path=.pf/artifacts/shell-report.md,type=markdown,required=true",
            "--expected-report-artifact",
            ".pf/artifacts/shell-report.md",
            "--apply",
        )
        pf("worker-run", "start", "--project-root", str(project), "--task", "shell-task", "--driver", "test-shell-agent")
        pf("worker-run", "collect", "--project-root", str(project), "--task", "shell-task")
        command = json.loads((project / ".pf/runtime/agent-runs/shell-run/shell-task/command.json").read_text(encoding="utf-8"))
        env = command["command"]["environment"]
        if "PF_LEAK_TEST_SECRET" in env:
            raise AssertionError("isolated worker command environment contains leaked parent variable")
        report = (project / ".pf/artifacts/shell-report.md").read_text(encoding="utf-8")
        if "- leak_keys: `0`" not in report:
            raise AssertionError("shell worker reported leaked PF_LEAK_TEST variables")
        if not (project / ".pf/runtime/agent-runs/shell-run/shell-task/process.json").is_file():
            raise AssertionError("shell worker did not write process proof")
        assignment = project / ".pf/assignments/shell-task.yaml"
        assignment.write_text(assignment.read_text(encoding="utf-8") + "\nimmutability_probe: changed-after-capsule\n", encoding="utf-8")
        stale = pf("worker-run", "prepare", "--project-root", str(project), "--task", "shell-task", "--driver", "test-shell-agent", expect=1)
        if "assignment capsule is stale" not in (stale.stdout + stale.stderr):
            raise AssertionError("worker-run prepare did not reject stale assignment capsule")
    print("PASS: worker-run shell smoke")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
