#!/usr/bin/env python3
"""Smoke test for ProcessForge multi-agent orchestration process."""

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
DEFAULT_TIMEOUT = 90


def run_cli(*args: str, expect: int = 0, timeout: int = DEFAULT_TIMEOUT) -> CommandResult:
    result = run_processforge_command([sys.executable, str(CLI), *args], cwd=ROOT, timeout=timeout)
    if result.timed_out:
        raise AssertionError("timeout after command: " + " ".join(args) + "\n" + diagnostic_text(result))
    if result.returncode != expect:
        raise AssertionError(f"expected {expect}, got {result.returncode}: {' '.join(args)}\n{diagnostic_text(result)}")
    return result


def assert_file(path: Path) -> None:
    if not path.is_file():
        raise AssertionError(f"missing file: {path}")


def assert_contains(path: Path, needle: str) -> None:
    text = path.read_text(encoding="utf-8", errors="replace")
    if needle not in text:
        raise AssertionError(f"{path} does not contain {needle!r}")


def write_plan(path: Path, *, overlap: bool = False, missing_output_path: bool = False) -> None:
    docs_allowed = ".pf/artifacts/**" if overlap else "docs/**"
    docs_output_path = "" if missing_output_path else ".pf/artifacts/example-docs-worker-report.md"
    path.write_text(
        f"""schema_version: 1
run:
  id: example-run
  title: Example multi-agent run
  process: multi-agent-task-orchestration
orchestrator:
  role: orchestrator
  responsibilities:
    - decompose work
    - assign workers
    - review outputs
    - integrate final result
workers:
  -
    id: example-docs-worker
    title: Documentation update
    role: documentation
    process: content-production
    execution_mode: docs_only
    writer: true
    allowed_files:
      - {docs_allowed}
      - README.md
    allowed_read_files:
      - .pf/contexts/project-context.snapshot.yaml
    forbidden_files:
      - tools/**
      - schemas/**
    required_sources:
      - .pf/contexts/project-context.snapshot.yaml
    required_outputs:
      -
        id: docs-report
        path: {docs_output_path}
        type: markdown
        required: true
    expected_report_artifact: .pf/artifacts/example-docs-worker-report.md
    dependencies: []
    worker_may_rebuild_context: false
  -
    id: example-test-worker
    title: Release test verification
    role: release-assurance
    process: testing
    execution_mode: assurance
    writer: true
    allowed_files:
      - .pf/artifacts/**
    allowed_read_files:
      - tools/**
      - schemas/**
      - .pf/contexts/project-context.snapshot.yaml
    forbidden_files:
      - tools/processforge.py
    required_sources:
      - .pf/contexts/project-context.snapshot.yaml
    required_outputs:
      -
        id: test-report
        path: .pf/artifacts/example-test-worker-report.md
        type: markdown
        required: true
    expected_report_artifact: .pf/artifacts/example-test-worker-report.md
    dependencies: []
    worker_may_rebuild_context: false
integration:
  required: true
  role: orchestrator
  expected_output: .pf/artifacts/example-integration-report.md
""",
        encoding="utf-8",
    )


def make_project(root: Path, name: str) -> Path:
    workplace = root / f"{name}-workplace"
    project = root / name
    project.mkdir()
    (project / "README.md").write_text(f"# {name}\n", encoding="utf-8")
    (project / "docs").mkdir()
    (project / "docs" / "index.md").write_text("# Docs\n", encoding="utf-8")
    (project / "tools").mkdir()
    (project / "tools" / "fixture.py").write_text("# fixture\n", encoding="utf-8")
    (project / "schemas").mkdir()
    (project / "schemas" / "fixture.schema.json").write_text("{}\n", encoding="utf-8")
    run_cli("workplace-init", "--workplace", str(workplace), "--apply")
    run_cli("project-onboard", "--project-root", str(project), "--workplace", str(workplace), "--type", "generic-software-project", "--apply")
    return project


def positive(root: Path) -> None:
    project = make_project(root, "positive")
    plan_source = root / "orchestrator-task-plan.yaml"
    write_plan(plan_source)
    run_cli("orchestrator-plan", "create", "--project-root", str(project), "--run", "example-run", "--title", "Example multi-agent run", "--answers", str(plan_source), "--apply")
    plan = project / ".pf" / "runs" / "example-run" / "orchestrator-plan.yaml"
    run_cli("orchestrator-plan", "validate", "--project-root", str(project), "--plan", str(plan))
    run_cli("orchestrator-plan", "apply", "--project-root", str(project), "--plan", str(plan), "--apply")
    run_cli("orchestrator-plan", "status", "--project-root", str(project), "--run", "example-run")
    run_cli("worker-launch-prompt", "create", "--project-root", str(project), "--task", "example-docs-worker", "--apply")
    for rel_path in [
        ".pf/runs/example-run/run.yaml",
        ".pf/runs/example-run/orchestrator-plan.yaml",
        ".pf/runs/example-run/worker-prompts/example-docs-worker.md",
        ".pf/runs/example-run/worker-prompts/example-test-worker.md",
        ".pf/runs/example-run/orchestration-task-index.md",
        ".pf/runs/example-run/orchestration-summary.md",
        ".pf/assignments/example-docs-worker.yaml",
        ".pf/assignments/example-test-worker.yaml",
        ".pf/contexts/assignment-capsules/example-docs-worker.capsule.yaml",
        ".pf/contexts/assignment-capsules/example-test-worker.capsule.yaml",
        ".pf/handoffs/runs/example-run-orchestrator-handoff.md",
    ]:
        assert_file(project / rel_path)
    prompt = project / ".pf" / "runs" / "example-run" / "worker-prompts" / "example-docs-worker.md"
    assert_contains(prompt, "You are not the orchestrator.")
    assert_contains(prompt, "Do not rebuild full project context unless explicitly allowed.")
    assert_contains(prompt, "allowed_files")
    capsule = project / ".pf" / "contexts" / "assignment-capsules" / "example-docs-worker.capsule.yaml"
    assert_contains(capsule, "worker_may_rebuild_context: false")
    capsule_text = capsule.read_text(encoding="utf-8", errors="replace")
    if "full_project_context" in capsule_text:
        raise AssertionError("capsule contains full_project_context marker")
    run_cli("run-doctor", "--project-root", str(project), "--run", "example-run")
    run_cli("task-doctor", "--project-root", str(project), "--task", "example-docs-worker")


def negative(root: Path) -> None:
    project = make_project(root, "negative")
    overlap = root / "overlap.yaml"
    write_plan(overlap, overlap=True)
    run_cli("orchestrator-plan", "validate", "--project-root", str(project), "--plan", str(overlap), expect=1)
    missing = root / "missing-output.yaml"
    write_plan(missing, missing_output_path=True)
    run_cli("orchestrator-plan", "validate", "--project-root", str(project), "--plan", str(missing), expect=1)


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="pf-orchestration-") as temp:
        root = Path(temp)
        positive(root)
        negative(root)
    print("PASS: multi-agent orchestration smoke")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
