#!/usr/bin/env python3
"""Smoke test for Director/Ledger/Execution Inspector responsibility boundaries."""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path
from typing import Any

import yaml

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


def read_yaml(path: Path) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8")) if path.is_file() else {}
    return data if isinstance(data, dict) else {}


def read_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}
    return data if isinstance(data, dict) else {}


def lease_files(workplace: Path) -> list[Path]:
    return sorted((workplace / "runtime" / "agent-leases").glob("*.yaml"))


def ledger_text(workplace: Path) -> str:
    path = workplace / "runtime" / "agent-ledger" / "sessions.ndjson"
    return path.read_text(encoding="utf-8") if path.is_file() else ""


def assert_no_agent_runs(project: Path, message: str) -> None:
    agent_runs = project / ".pf" / "runtime" / "agent-runs"
    if agent_runs.exists() and any(agent_runs.rglob("*")):
        raise AssertionError(message)


def write_route(project: Path) -> None:
    (project / ".pf" / "process-routes.yaml").write_text(
        """schema_version: 1
routes:
  - id: feature-to-worker
    from_process: feature-development
    to_process: task-execution
    mode: wait_for_result
    requires_agent:
      role: worker
      status: checked_in
    input_contract:
      required_artifacts: []
    output_contract:
      expected_artifacts: []
    return:
      to_process: feature-development
      to_stage: integration
      continue_run: true
""",
        encoding="utf-8",
    )


def write_plan(path: Path) -> None:
    path.write_text(
        """schema_version: 1
run:
  id: inspector-run
  title: Inspector run
  process: multi-agent-task-orchestration
orchestrator:
  role: agent-director
runtime:
  default_driver: test-shell-agent
  supervisor_profile: default
  start_policy: manual
workers:
  - id: inspected-worker
    title: Inspected worker
    role: worker
    process: testing
    execution_mode: assurance
    writer: true
    allowed_files: [.pf/artifacts/**]
    allowed_read_files: [.pf/contexts/project-context.snapshot.yaml]
    forbidden_files: []
    required_sources: [.pf/contexts/project-context.snapshot.yaml]
    required_outputs:
      - id: inspected-report
        path: .pf/artifacts/inspected-report.md
        type: markdown
        required: true
    expected_report_language: en
    expected_report_artifact: .pf/artifacts/inspected-report.md
    runtime_driver: test-shell-agent
    worker_may_rebuild_context: false
integration:
  required: false
  role: agent-director
  expected_output: .pf/artifacts/director-inspector-integration.md
""",
        encoding="utf-8",
    )


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="pf-director-inspector-") as temp:
        root = Path(temp)
        workplace = root / "workplace"
        project = root / "project"
        project.mkdir()
        (project / "README.md").write_text("# Director inspector boundary smoke\n", encoding="utf-8")

        pf("workplace-init", "--workplace", str(workplace), "--apply")
        pf("project-onboard", "--project-root", str(project), "--workplace", str(workplace), "--type", "generic-software-project", "--apply")
        pf("agent-register", "--workplace", str(workplace), "--agent", "director-local", "--role", "agent-director")
        pf("agent-register", "--workplace", str(workplace), "--agent", "worker-local", "--role", "worker")
        pf("agent-checkin", "--workplace", str(workplace), "--agent", "director-local", "--session", "sess-director-001", "--role", "agent-director")

        write_route(project)
        pf("handoff-create", "--project-root", str(project), "--route", "feature-to-worker", "--from-run", "feature-run", "--id", "handoff-boundary", "--apply")
        pf("agent-director-tick", "--workplace", str(workplace), "--project-root", str(project))
        handoff = read_yaml(project / ".pf" / "handoffs" / "handoff-boundary" / "handoff.yaml")
        if handoff.get("status") != "waiting_for_agent":
            raise AssertionError(f"director should leave handoff waiting without worker; got {handoff.get('status')}")
        if lease_files(workplace):
            raise AssertionError("director should not grant a lease before a matching worker is checked in")
        assert_no_agent_runs(project, "director created worker runtime files while only routing a handoff")

        pf("agent-checkin", "--workplace", str(workplace), "--agent", "worker-local", "--session", "sess-worker-001", "--role", "worker")
        pf("agent-director-tick", "--workplace", str(workplace), "--project-root", str(project))
        handoff = read_yaml(project / ".pf" / "handoffs" / "handoff-boundary" / "handoff.yaml")
        assigned = handoff.get("assigned_agent") if isinstance(handoff.get("assigned_agent"), dict) else {}
        if handoff.get("status") != "ready" or assigned.get("agent_id") != "worker-local":
            raise AssertionError("director did not assign the checked-in worker to the handoff")
        leases_before = [item.name for item in lease_files(workplace)]
        if leases_before != ["lease-handoff-boundary-worker-local.yaml"]:
            raise AssertionError(f"unexpected director lease set: {leases_before}")
        ledger_before_inspector = ledger_text(workplace)
        assert_no_agent_runs(project, "director created worker runtime files after marking handoff ready")

        plan = root / "inspector-plan.yaml"
        write_plan(plan)
        pf("orchestrator-plan", "validate", "--project-root", str(project), "--plan", str(plan))
        pf("orchestrator-plan", "apply", "--project-root", str(project), "--plan", str(plan), "--apply")
        assert_no_agent_runs(project, "orchestrator plan apply should not start runtime workers with manual start_policy")

        pf("execution-inspector-run", "--project-root", str(project), "--run", "inspector-run", "--interval", "0", "--max-ticks", "2", "--final-drain-timeout", "5", timeout=180)
        runtime_root = project / ".pf" / "runtime" / "agent-runs" / "inspector-run" / "inspected-worker"
        for name in ["status.json", "command.json", "process.json", "heartbeat.json", "exit.json", "stdout.log", "stderr.log"]:
            if not (runtime_root / name).is_file():
                raise AssertionError(f"execution inspector did not produce runtime proof: {name}")
        status = read_json(runtime_root / "status.json")
        if status.get("status") != "completed":
            raise AssertionError(f"worker runtime should be completed, got {status.get('status')}")
        assignment = read_yaml(project / ".pf" / "assignments" / "inspected-worker.yaml")
        if assignment.get("status") not in {"done", "completed"}:
            raise AssertionError(f"execution inspector did not collect the completed task, got {assignment.get('status')}")
        if not (project / ".pf" / "artifacts" / "inspected-report.md").is_file():
            raise AssertionError("worker report was not collected as a required output")

        leases_after = [item.name for item in lease_files(workplace)]
        if leases_after != leases_before:
            raise AssertionError(f"execution inspector changed workplace leases: before={leases_before} after={leases_after}")
        if ledger_text(workplace) != ledger_before_inspector:
            raise AssertionError("execution inspector wrote workplace ledger events")
        handoff_after = read_yaml(project / ".pf" / "handoffs" / "handoff-boundary" / "handoff.yaml")
        if handoff_after != handoff:
            raise AssertionError("execution inspector changed handoff/director state")

    print("PASS: director ledger execution inspector boundary smoke")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
