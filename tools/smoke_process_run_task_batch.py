#!/usr/bin/env python3
"""Smoke test for ProcessForge Process Run / Task Batch MVP."""

from __future__ import annotations

import json
import re
import sys
import tempfile
from pathlib import Path

from processforge_subprocess import CommandResult, diagnostic_text, run_command as run_processforge_command


ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "tools" / "processforge.py"
DEFAULT_TIMEOUT = 60
PRIVATE_PATH_PATTERN = re.compile(r"[A-Za-z]:[\\/]|/[Uu]sers/|/[Hh]ome/")


def run_cmd(command: list[str], cwd: Path = ROOT, timeout: int = DEFAULT_TIMEOUT, expect: int = 0) -> CommandResult:
    result = run_processforge_command(command, cwd=cwd, timeout=timeout)
    if result.timed_out:
        print("FAIL smoke_process_run_task_batch: timeout")
        print(diagnostic_text(result))
        raise AssertionError(f"timeout after {timeout}s: {' '.join(command)}")
    if result.returncode != expect:
        print("FAIL smoke_process_run_task_batch: unexpected command exit")
        print(f"Expected exit code: {expect}")
        print(diagnostic_text(result))
        raise AssertionError(f"expected exit {expect}, got {result.returncode}: {' '.join(command)}")
    return result


def pf(*args: str, expect: int = 0) -> CommandResult:
    return run_cmd([sys.executable, str(CLI), *args], expect=expect)


def assert_file(path: Path) -> None:
    if not path.is_file():
        raise AssertionError(f"missing file: {path}")


def assert_contains(path: Path, needle: str) -> None:
    text = path.read_text(encoding="utf-8", errors="replace")
    if needle not in text:
        raise AssertionError(f"{path} does not contain {needle!r}")


def assert_no_private_paths(paths: list[Path]) -> None:
    for path in paths:
        text = path.read_text(encoding="utf-8", errors="replace")
        if PRIVATE_PATH_PATTERN.search(text):
            raise AssertionError(f"private absolute path marker found in {path}")


def make_project(root: Path, name: str) -> Path:
    workplace = root / f"{name}-workplace"
    project = root / name
    project.mkdir(parents=True)
    (project / "README.md").write_text(f"# {name}\n", encoding="utf-8")
    pf("workplace-init", "--workplace", str(workplace), "--apply")
    pf("project-onboard", "--project-root", str(project), "--workplace", str(workplace), "--type", "generic-software-project", "--apply")
    return project


def event_types(project: Path) -> list[str]:
    events = project / ".pf" / "runtime" / "events" / "events.ndjson"
    values: list[str] = []
    for line in events.read_text(encoding="utf-8", errors="replace").splitlines():
        if not line.strip():
            continue
        values.append(str(json.loads(line).get("event_type", "")))
    return values


def positive_workflow(root: Path) -> None:
    project = make_project(root, "positive")
    run_id = "release-prep"
    pf("run-create", "--project-root", str(project), "--id", run_id, "--title", "Release preparation", "--process", "task-batch-execution", "--apply")
    pf("agent-start-prompt", "--project-root", str(project))
    assert_contains(project / ".pf" / "START_AGENT_HERE.md", "run-status --project-root . --run release-prep")
    pf("task-create", "--project-root", str(project), "--run", run_id, "--id", "task-001-fix", "--title", "Fix task", "--process", "bug-fix", "--apply")
    pf("iteration-add", "--project-root", str(project), "--task", "task-001-fix", "--kind", "work", "--summary", "Implemented first fix.", "--apply")
    pf("iteration-add", "--project-root", str(project), "--task", "task-001-fix", "--kind", "debug", "--status", "failed", "--summary", "Initial debug failed.", "--apply")
    pf("iteration-add", "--project-root", str(project), "--task", "task-001-fix", "--kind", "fix", "--summary", "Adjusted the fix.", "--apply")
    pf("iteration-add", "--project-root", str(project), "--task", "task-001-fix", "--kind", "debug", "--status", "passed", "--summary", "Debug passed.", "--apply")
    pf("task-complete", "--project-root", str(project), "--task", "task-001-fix", "--summary", "Fix complete.", "--apply")
    pf("task-create", "--project-root", str(project), "--run", run_id, "--id", "task-002-test", "--title", "Test task", "--process", "testing", "--apply")
    pf("iteration-add", "--project-root", str(project), "--task", "task-002-test", "--kind", "work", "--summary", "Prepared test.", "--apply")
    pf("iteration-add", "--project-root", str(project), "--task", "task-002-test", "--kind", "debug", "--status", "passed", "--summary", "Test passed.", "--apply")
    pf("task-complete", "--project-root", str(project), "--task", "task-002-test", "--summary", "Test complete.", "--apply")
    pf("run-summary", "--project-root", str(project), "--run", run_id, "--apply")
    pf("run-doctor", "--project-root", str(project), "--run", run_id)
    pf("task-doctor", "--project-root", str(project), "--task", "task-001-fix")
    pf("run-complete", "--project-root", str(project), "--run", run_id, "--apply")
    pf("run-doctor", "--project-root", str(project), "--run", run_id)
    status = pf("run-status", "--project-root", str(project), "--run", run_id).stdout
    if "STATUS: completed" not in status:
        raise AssertionError("run-status did not report completed")
    assert_file(project / ".pf" / "runs" / run_id / "summary.md")
    assert_file(project / ".pf" / "handoffs" / "runs" / f"{run_id}-handoff.md")
    assert_no_private_paths(
        [
            project / ".pf" / "runs" / run_id / "run.yaml",
            project / ".pf" / "assignments" / "task-001-fix.yaml",
            project / ".pf" / "assignments" / "task-002-test.yaml",
        ]
    )
    events = event_types(project)
    for expected in ["run.created", "task.created", "assignment.created", "iteration.added", "task.completed", "assignment.completed", "run.summary.created", "run.completed"]:
        if expected not in events:
            raise AssertionError(f"missing event: {expected}")
    outbox = project / ".pf" / "runtime" / "hooks" / "outbox" / "wtaicc"
    if not any("run.completed" in path.read_text(encoding="utf-8", errors="replace") for path in outbox.glob("*.json")):
        raise AssertionError("run.completed was not written to hooks outbox")


def negative_workflow(root: Path) -> None:
    project = make_project(root, "negative")
    pf("task-create", "--project-root", str(project), "--run", "missing-run", "--id", "task-001", "--title", "Missing run", "--process", "bug-fix", "--apply", expect=1)
    pf("iteration-add", "--project-root", str(project), "--task", "missing-task", "--kind", "work", "--summary", "Missing task", "--apply", expect=1)
    pf("run-create", "--project-root", str(project), "--id", "negative-run", "--title", "Negative run", "--process", "task-batch-execution", "--apply")
    pf("task-create", "--project-root", str(project), "--run", "negative-run", "--id", "task-001-dup", "--title", "Duplicate", "--process", "bug-fix", "--apply")
    pf("task-create", "--project-root", str(project), "--run", "negative-run", "--id", "task-001-dup", "--title", "Duplicate", "--process", "bug-fix", "--apply", expect=1)
    pf("iteration-add", "--project-root", str(project), "--task", "task-001-dup", "--id", "iter-010", "--kind", "work", "--summary", "First iteration.", "--apply")
    pf("iteration-add", "--project-root", str(project), "--task", "task-001-dup", "--id", "iter-010", "--kind", "work", "--summary", "Duplicate iteration.", "--apply", expect=1)
    pf("run-complete", "--project-root", str(project), "--run", "negative-run", "--apply", expect=1)
    task_path = project / ".pf" / "assignments" / "task-001-dup.yaml"
    text = task_path.read_text(encoding="utf-8")
    text = text.replace("status: open", "status: done")
    text = text.replace("summary: \"\"", "summary: \"\"")
    task_path.write_text(text, encoding="utf-8")
    pf("task-doctor", "--project-root", str(project), "--task", "task-001-dup", expect=1)
    run_path = project / ".pf" / "runs" / "negative-run" / "run.yaml"
    private_probe = "C" + ":" + "\\\\Temp\\\\secret.txt"
    run_path.write_text(run_path.read_text(encoding="utf-8") + f"\nprivate_probe: {private_probe}\n", encoding="utf-8")
    pf("run-doctor", "--project-root", str(project), "--run", "negative-run", expect=1)


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="pf-run-task-smoke-") as temp:
        root = Path(temp)
        positive_workflow(root)
        negative_workflow(root)
    print("PASS: smoke_process_run_task_batch")
    return 0


if __name__ == "__main__":
    sys.exit(main())
