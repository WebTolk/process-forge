#!/usr/bin/env python3
"""Smoke test that multi-agent orchestration composes separate agent sessions."""

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


def rows(stdout: str) -> list[dict[str, object]]:
    data = json.loads(stdout)
    if isinstance(data, list):
        return [item for item in data if isinstance(item, dict)]
    if isinstance(data, dict):
        return [data]
    return []


def write_plan(path: Path) -> None:
    path.write_text(
        """schema_version: 1
run:
  id: composed-sessions-run
  title: Composed sessions run
  process: multi-agent-task-orchestration
orchestrator:
  role: agent-director
runtime:
  default_driver: manual
  supervisor_profile: default
  start_policy: manual
workers:
  - id: docs-worker
    title: Docs worker
    role: docs
    process: task-batch-execution
    execution_mode: docs_only
    writer: true
    allowed_files: [.pf/artifacts/docs-worker.md]
    allowed_read_files: [.pf/contexts/project-context.snapshot.yaml]
    forbidden_files: []
    required_sources: [.pf/contexts/project-context.snapshot.yaml]
    required_outputs:
      - id: docs-report
        path: .pf/artifacts/docs-worker.md
        type: markdown
        required: true
    expected_report_artifact: .pf/artifacts/docs-worker.md
    runtime_driver: manual
  - id: test-worker
    title: Test worker
    role: test
    process: task-batch-execution
    execution_mode: assurance
    writer: true
    allowed_files: [.pf/artifacts/test-worker.md]
    allowed_read_files: [.pf/contexts/project-context.snapshot.yaml]
    forbidden_files: []
    required_sources: [.pf/contexts/project-context.snapshot.yaml]
    required_outputs:
      - id: test-report
        path: .pf/artifacts/test-worker.md
        type: markdown
        required: true
    expected_report_artifact: .pf/artifacts/test-worker.md
    runtime_driver: manual
integration:
  required: false
  role: agent-director
  expected_output: .pf/artifacts/integration.md
""",
        encoding="utf-8",
    )


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="pf-multi-agent-sessions-") as temp:
        root = Path(temp)
        workplace = root / "workplace"
        project = root / "project"
        plan = root / "plan.yaml"
        project.mkdir()
        (project / "README.md").write_text("# Multi-agent composed sessions smoke\n", encoding="utf-8")

        pf("workplace-init", "--workplace", str(workplace), "--apply")
        pf("project-onboard", "--project-root", str(project), "--workplace", str(workplace), "--type", "generic-software-project", "--apply")
        pf("session-start", "--workplace", str(workplace), "--project-root", str(project), "--agent", "director-local", "--session", "sess-director", "--process", "multi-agent-task-orchestration", "--role", "agent-director")
        pf("agent-checkin", "--workplace", str(workplace), "--project-root", str(project), "--agent", "docs-agent", "--session", "sess-docs", "--process", "documentation", "--role", "docs")
        pf("agent-checkin", "--workplace", str(workplace), "--project-root", str(project), "--agent", "test-agent", "--session", "sess-test", "--process", "task-batch-execution", "--role", "test")

        write_plan(plan)
        pf("orchestrator-plan", "validate", "--project-root", str(project), "--plan", str(plan))
        pf("orchestrator-plan", "apply", "--project-root", str(project), "--plan", str(plan), "--workplace", str(workplace), "--apply")
        for task in ["docs-worker", "test-worker"]:
            if not (project / ".pf" / "assignments" / f"{task}.yaml").is_file():
                raise AssertionError(f"assignment missing for {task}")
            if not (project / ".pf" / "contexts" / "assignment-capsules" / f"{task}.capsule.yaml").is_file():
                raise AssertionError(f"capsule missing for {task}")
        if not (workplace / "runtime" / "agent-leases" / "lease-composed-sessions-run-docs-worker.yaml").is_file():
            raise AssertionError("orchestration lease missing for docs worker")
        agent_runs = project / ".pf" / "runtime" / "agent-runs"
        if agent_runs.exists() and any(agent_runs.rglob("*")):
            raise AssertionError("manual multi-agent composition should not start shell runtime workers")

        active = {str(item.get("session_id")): str(item.get("status")) for item in rows(pf("agent-status", "--workplace", str(workplace), "--json").stdout)}
        for session_id in ["sess-director", "sess-docs", "sess-test"]:
            if active.get(session_id) != "online":
                raise AssertionError(f"{session_id} should be online, got {active}")
        pf("agent-checkout", "--workplace", str(workplace), "--session", "sess-docs")
        after_docs = {str(item.get("session_id")): str(item.get("status")) for item in rows(pf("agent-status", "--workplace", str(workplace), "--json").stdout)}
        if after_docs.get("sess-docs") != "checked_out" or after_docs.get("sess-test") != "online":
            raise AssertionError(f"worker sessions should checkout independently, got {after_docs}")
        pf("agent-checkout", "--workplace", str(workplace), "--session", "sess-test")
        pf("agent-checkout", "--workplace", str(workplace), "--session", "sess-director")

    print("PASS: multi-agent as composed sessions smoke")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
