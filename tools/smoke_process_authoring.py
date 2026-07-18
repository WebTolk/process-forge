#!/usr/bin/env python3
"""Smoke test for ProcessForge Process Authoring MVP."""

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
        print("FAIL smoke_process_authoring: timeout")
        print(diagnostic_text(result))
        raise AssertionError(f"timeout after {timeout}s: {' '.join(command)}")
    if result.returncode != expect:
        print("FAIL smoke_process_authoring: unexpected command exit")
        print(f"Expected exit code: {expect}")
        print(diagnostic_text(result))
        raise AssertionError(f"expected exit {expect}, got {result.returncode}: {' '.join(command)}")
    return result


def pf(*args: str, expect: int = 0, timeout: int = DEFAULT_TIMEOUT) -> CommandResult:
    return run_cmd([sys.executable, str(CLI), *args], expect=expect, timeout=timeout)


def assert_file(path: Path) -> None:
    if not path.is_file():
        raise AssertionError(f"missing file: {path}")


def assert_contains(path: Path, needle: str) -> None:
    text = path.read_text(encoding="utf-8", errors="replace")
    if needle not in text:
        raise AssertionError(f"{path} does not contain {needle!r}")


def assert_no_private_paths(paths: list[Path]) -> None:
    forbidden_shell = "Power" + "Shell"
    forbidden_script = "." + "ps1"
    for path in paths:
        text = path.read_text(encoding="utf-8", errors="replace")
        if PRIVATE_PATH_PATTERN.search(text):
            raise AssertionError(f"private absolute path marker found in {path}")
        lower = text.lower()
        if forbidden_shell.lower() in lower or forbidden_script in lower:
            raise AssertionError(f"unsupported shell reference found in {path}")


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
        if line.strip():
            values.append(str(json.loads(line).get("event_type", "")))
    return values


def write_answers(path: Path, body: str) -> Path:
    path.write_text(body.strip() + "\n", encoding="utf-8")
    return path


def positive_workflow(root: Path) -> None:
    project = make_project(root, "positive")
    process_id = "seo-audit"
    pf("process-authoring-start", "--project-root", str(project), "--id", process_id, "--title", "SEO Audit", "--apply")
    session = project / ".pf" / "authoring" / "processes" / process_id
    assert_file(session / "answers.yaml")
    assert_file(session / "draft.process.yaml")
    assert_contains(session / "questions.md", "Process Authoring Questions")
    pf("process-authoring-review", "--project-root", str(project), "--process", process_id)
    assert_contains(session / "logic-review.md", "Result: `pass`")
    pf("process-authoring-apply", "--project-root", str(project), "--process", process_id)
    for path in [
        project / "processes" / f"{process_id}.yaml",
        project / "prompts" / f"{process_id}-agent.md",
        project / "docs" / "processes" / f"{process_id}.md",
        project / "examples" / "process-authoring" / process_id / "README.md",
        project / "examples" / "process-authoring" / process_id / "process-authoring-seo-audit-report.md",
        project / "examples" / "process-authoring" / process_id / "process-authoring-seo-audit-review.md",
        project / "examples" / "process-authoring" / process_id / "process-authoring-seo-audit-handoff.md",
    ]:
        assert_file(path)
    pf("process-doctor", "--project-root", str(project), "--process", process_id)
    if process_id not in pf("process-list", "--project-root", str(project)).stdout:
        raise AssertionError("process-list did not include authored process")
    if "STAGES:" not in pf("process-describe", "--project-root", str(project), "--process", process_id).stdout:
        raise AssertionError("process-describe did not print stages")
    run_id = "seo-audit-run"
    pf("run-create", "--project-root", str(project), "--id", run_id, "--title", "SEO audit run", "--process", process_id, "--apply")
    pf("task-create", "--project-root", str(project), "--run", run_id, "--id", "task-001-audit", "--title", "Audit task", "--process", process_id, "--apply")
    pf("iteration-add", "--project-root", str(project), "--task", "task-001-audit", "--kind", "work", "--summary", "Initial audit work.", "--apply")
    pf("iteration-add", "--project-root", str(project), "--task", "task-001-audit", "--kind", "debug", "--summary", "Checked missing evidence.", "--apply")
    pf("task-complete", "--project-root", str(project), "--task", "task-001-audit", "--summary", "Audit task completed.", "--apply")
    pf("run-summary", "--project-root", str(project), "--run", run_id, "--apply")
    pf("run-doctor", "--project-root", str(project), "--run", run_id)
    assert_no_private_paths(
        [
            project / "processes" / f"{process_id}.yaml",
            project / "prompts" / f"{process_id}-agent.md",
            project / "docs" / "processes" / f"{process_id}.md",
            project / ".pf" / "runs" / run_id / "run.yaml",
            project / ".pf" / "assignments" / "task-001-audit.yaml",
        ]
    )
    events = event_types(project)
    for expected in [
        "process_authoring.started",
        "process_authoring.answers.created",
        "process_authoring.draft.created",
        "process_authoring.logic_review.created",
        "process_authoring.applied",
        "process_authoring.completed",
        "process.created",
        "process.doctor.passed",
        "run.created",
        "task.created",
        "iteration.added",
        "task.completed",
        "run.summary.created",
    ]:
        if expected not in events:
            raise AssertionError(f"missing event: {expected}")
    outbox = project / ".pf" / "runtime" / "hooks" / "outbox" / "wtaicc"
    if not any("process.created" in path.read_text(encoding="utf-8", errors="replace") for path in outbox.glob("*.json")):
        raise AssertionError("process.created was not written to hooks outbox")


def negative_workflow(root: Path) -> None:
    project = make_project(root, "negative")
    duplicate = write_answers(
        root / "duplicate-stage.yaml",
        """
schema_version: 1
process: {id: duplicate-stage, name: Duplicate Stage, description: Duplicate stage ids fail review.}
roles: [{id: author, title: Author}]
stages:
  - {id: intake, title: Intake, required_role: author, produced_artifacts: [brief], exit_gates: [brief-approved]}
  - {id: intake, title: Intake Again, required_role: author, produced_artifacts: [brief], exit_gates: [brief-approved]}
artifacts: [{id: brief, title: Brief, owner_role: author}]
gates: [{id: brief-approved, description: Brief approved, blocking: true, required_artifact: brief}]
""",
    )
    pf("process-authoring-start", "--project-root", str(project), "--answers", str(duplicate), "--apply")
    pf("process-authoring-review", "--project-root", str(project), "--process", "duplicate-stage", expect=1)

    missing_artifact = write_answers(
        root / "missing-gate-artifact.yaml",
        """
schema_version: 1
process: {id: missing-gate-artifact, name: Missing Gate Artifact, description: Missing gate artifact fails review.}
roles: [{id: author, title: Author}]
stages: [{id: intake, title: Intake, required_role: author, produced_artifacts: [brief], exit_gates: [brief-approved]}]
artifacts: [{id: brief, title: Brief, owner_role: author}]
gates: [{id: brief-approved, description: Brief approved, blocking: true, required_artifact: missing-review}]
""",
    )
    pf("process-authoring-start", "--project-root", str(project), "--answers", str(missing_artifact), "--apply")
    pf("process-authoring-review", "--project-root", str(project), "--process", "missing-gate-artifact", expect=1)

    handoff_before_review = write_answers(
        root / "handoff-before-review.yaml",
        """
schema_version: 1
process: {id: handoff-before-review, name: Handoff Before Review, description: Handoff warning is visible.}
roles: [{id: author, title: Author}, {id: reviewer, title: Reviewer}]
stages:
  - {id: handoff, title: Handoff, required_role: author, produced_artifacts: [handoff], exit_gates: [handoff-created], handoff_required: true}
  - {id: review, title: Review, required_role: reviewer, produced_artifacts: [review-notes], exit_gates: [review-passed]}
artifacts:
  - {id: handoff, title: Handoff, owner_role: author}
  - {id: review-notes, title: Review Notes, owner_role: reviewer}
gates:
  - {id: handoff-created, description: Handoff exists, blocking: true, required_artifact: handoff}
  - {id: review-passed, description: Review passed, blocking: true, required_artifact: review-notes}
""",
    )
    pf("process-authoring-start", "--project-root", str(project), "--answers", str(handoff_before_review), "--apply")
    warning = pf("process-authoring-review", "--project-root", str(project), "--process", "handoff-before-review").stdout
    if "WARN" not in warning:
        raise AssertionError("handoff-before-review did not produce a warning")

    missing_loop = write_answers(
        root / "missing-task-loop.yaml",
        """
schema_version: 1
process: {id: missing-task-loop, name: Missing Task Loop, description: Multi-task without loop fails review.}
run_model: {supports_multiple_tasks: true, default_task_loop: {enabled: false, iteration_kinds: []}}
roles: [{id: author, title: Author}]
stages: [{id: intake, title: Intake, required_role: author, produced_artifacts: [brief], exit_gates: [brief-approved]}]
artifacts: [{id: brief, title: Brief, owner_role: author}]
gates: [{id: brief-approved, description: Brief approved, blocking: true, required_artifact: brief}]
""",
    )
    pf("process-authoring-start", "--project-root", str(project), "--answers", str(missing_loop), "--apply")
    pf("process-authoring-review", "--project-root", str(project), "--process", "missing-task-loop", expect=1)

    pf("process-authoring-start", "--project-root", str(project), "--id", "doctor-missing-prompt", "--title", "Doctor Missing Prompt", "--apply")
    pf("process-authoring-apply", "--project-root", str(project), "--process", "doctor-missing-prompt")
    (project / "prompts" / "doctor-missing-prompt-agent.md").unlink()
    pf("process-doctor", "--project-root", str(project), "--process", "doctor-missing-prompt", expect=1)


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="pf-process-authoring-smoke-") as temp:
        root = Path(temp)
        positive_workflow(root)
        negative_workflow(root)
    print("PASS: smoke_process_authoring")
    return 0


if __name__ == "__main__":
    sys.exit(main())
