#!/usr/bin/env python3
"""Targeted smoke for shell-agent heartbeat proof contract."""

from __future__ import annotations

import json
import os
import sys
import tempfile
import time
from pathlib import Path

from processforge_subprocess import CommandResult, diagnostic_text, run_command as run_processforge_command


ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "tools" / "processforge.py"


def pf(*args: str, expect: int = 0, timeout: int = 120) -> CommandResult:
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
    (project / "README.md").write_text("# Shell heartbeat contract smoke\n", encoding="utf-8")
    pf("workplace-init", "--workplace", str(workplace), "--apply")
    pf("project-onboard", "--project-root", str(project), "--workplace", str(workplace), "--type", "generic-software-project", "--apply")
    return project


def write_profile(path: Path) -> None:
    path.write_text(
        """schema_version: 1
scheduling:
  max_parallel_workers: 2
loop:
  interval_seconds: 0.2
  max_ticks: 12
""",
        encoding="utf-8",
    )


def write_driver(path: Path, driver_id: str, mode: str, timeout_seconds: int, sleep_seconds: float = 0.0) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        f"""schema_version: 1
id: {driver_id}
title: {driver_id}
kind: shell
command:
  executable: "{{python_executable}}"
  args:
    - "{{processforge_root}}/tools/test_agents/pf_shell_agent.py"
    - "--capsule"
    - "{{capsule_path}}"
    - "--worker-prompt"
    - "{{worker_prompt_path}}"
    - "--output"
    - "{{expected_report_path}}"
    - "--heartbeat"
    - "{{heartbeat_path}}"
    - "--mode"
    - "{mode}"
    - "--sleep-seconds"
    - "{sleep_seconds}"
    - "--heartbeat-interval"
    - "0.2"
working_directory: "{{project_root}}"
environment:
  inherit: false
  variables: {{}}
io:
  stdin: none
  stdout: .pf/runtime/agent-runs/{{run_id}}/{{task_id}}/stdout.log
  stderr: .pf/runtime/agent-runs/{{run_id}}/{{task_id}}/stderr.log
heartbeat:
  mode: file
  path: .pf/runtime/agent-runs/{{run_id}}/{{task_id}}/heartbeat.json
  optional: false
limits:
  timeout_seconds: {timeout_seconds}
  max_retries: 0
security:
  allow_shell: false
  require_explicit_executable: false
  allow_network: false
""",
        encoding="utf-8",
    )


def install_local_drivers(project: Path) -> None:
    registry = project / ".pf/runtime/registries/runtime-drivers.local.yaml"
    driver_dir = project / ".pf/runtime/registries/runtime-drivers"
    write_driver(driver_dir / "slow-shell-agent.yaml", "slow-shell-agent", "sleep", 10, 2.0)
    write_driver(driver_dir / "fail-shell-agent.yaml", "fail-shell-agent", "fail", 10)
    registry.write_text(
        """schema_version: 1
runtime_drivers:
  - id: slow-shell-agent
    path: runtime-drivers/slow-shell-agent.yaml
    status: available
  - id: fail-shell-agent
    path: runtime-drivers/fail-shell-agent.yaml
    status: available
""",
        encoding="utf-8",
    )


def worker_block(task_id: str, driver: str) -> str:
    return f"""  - id: {task_id}
    title: {task_id}
    role: test
    process: testing
    execution_mode: assurance
    writer: true
    allowed_files: [.pf/artifacts/{task_id}-report.md]
    allowed_read_files: [.pf/contexts/project-context.snapshot.yaml]
    required_sources: [.pf/contexts/project-context.snapshot.yaml]
    required_outputs:
      - id: {task_id}-report
        path: .pf/artifacts/{task_id}-report.md
        type: markdown
        required: true
    expected_report_artifact: .pf/artifacts/{task_id}-report.md
    runtime_driver: {driver}
    worker_may_rebuild_context: false
"""


def write_plan(path: Path, run_id: str, workers: list[str], default_driver: str = "test-shell-agent") -> None:
    path.write_text(
        f"""schema_version: 1
run:
  id: {run_id}
  title: {run_id}
  process: multi-agent-task-orchestration
orchestrator:
  role: orchestrator
runtime:
  default_driver: {default_driver}
  supervisor_profile: default
  start_policy: supervisor
workers:
{''.join(workers)}integration:
  required: false
  role: orchestrator
  expected_output: .pf/artifacts/{run_id}-integration-report.md
""",
        encoding="utf-8",
    )


def apply_plan(project: Path, root: Path, run_id: str, workers: list[str]) -> None:
    plan = root / f"{run_id}.yaml"
    write_plan(plan, run_id, workers)
    pf("orchestrator-plan", "validate", "--project-root", str(project), "--plan", str(plan))
    pf("orchestrator-plan", "apply", "--project-root", str(project), "--plan", str(plan), "--apply")


def run_root(project: Path, run_id: str, task_id: str) -> Path:
    return project / ".pf/runtime/agent-runs" / run_id / task_id


def read_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def wait_for_json(path: Path, timeout_seconds: float = 5.0) -> dict[str, object]:
    deadline = time.perf_counter() + timeout_seconds
    last_error: Exception | None = None
    while time.perf_counter() < deadline:
        if path.is_file():
            try:
                return read_json(path)
            except json.JSONDecodeError as exc:
                last_error = exc
        time.sleep(0.1)
    if last_error:
        raise AssertionError(f"timed out waiting for valid JSON {path}: {last_error}")
    raise AssertionError(f"timed out waiting for JSON file: {path}")


def assert_heartbeat(heartbeat: dict[str, object], run_id: str, task_id: str, statuses: set[str]) -> None:
    if heartbeat.get("schema_version") != "1.0":
        raise AssertionError(f"heartbeat schema_version mismatch: {heartbeat}")
    if heartbeat.get("run_id") != run_id or heartbeat.get("task_id") != task_id:
        raise AssertionError(f"heartbeat identity mismatch: {heartbeat}")
    if heartbeat.get("status") not in statuses:
        raise AssertionError(f"heartbeat status mismatch: {heartbeat}")
    if not isinstance(heartbeat.get("pid"), int) or int(heartbeat["pid"]) <= 0:
        raise AssertionError(f"heartbeat missing pid: {heartbeat}")
    if not isinstance(heartbeat.get("sequence"), int):
        raise AssertionError(f"heartbeat missing sequence: {heartbeat}")
    if not heartbeat.get("timestamp"):
        raise AssertionError(f"heartbeat missing timestamp: {heartbeat}")


def wait_for_done(project: Path, run_id: str, expected_done: int, profile: Path, ticks: int = 12) -> None:
    for _index in range(ticks):
        pf("supervisor", "tick", "--project-root", str(project), "--run", run_id, "--profile", str(profile))
        status = pf("run-status", "--project-root", str(project), "--run", run_id).stdout
        if f"TASKS: done={expected_done}" in status:
            return
        time.sleep(0.25)
    raise AssertionError(f"run {run_id} did not reach done={expected_done}")


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="pf-shell-heartbeat-contract-", ignore_cleanup_errors=True) as temp:
        root = Path(temp)
        project = make_project(root)
        install_local_drivers(project)
        profile = root / "supervisor-profile.yaml"
        write_profile(profile)

        apply_plan(project, root, "wait-heartbeat-run", [worker_block("wait-agent", "test-shell-agent")])
        pf("worker-run", "start", "--project-root", str(project), "--task", "wait-agent", "--driver", "test-shell-agent", "--wait")
        wait_paths = run_root(project, "wait-heartbeat-run", "wait-agent")
        wait_heartbeat = wait_for_json(wait_paths / "heartbeat.json")
        assert_heartbeat(wait_heartbeat, "wait-heartbeat-run", "wait-agent", {"completed"})
        wait_report = (project / ".pf/artifacts/wait-agent-report.md").read_text(encoding="utf-8")
        if "- leak_keys: `0`" not in wait_report or "- run_id: `wait-heartbeat-run`" not in wait_report:
            raise AssertionError("wait-mode env isolation or canonical env proof failed")

        apply_plan(project, root, "detach-heartbeat-run", [worker_block("detach-agent", "slow-shell-agent")])
        pf("worker-run", "start", "--project-root", str(project), "--task", "detach-agent", "--driver", "slow-shell-agent", "--detach")
        detach_paths = run_root(project, "detach-heartbeat-run", "detach-agent")
        detach_state = wait_for_json(detach_paths / "status.json")
        if detach_state.get("status") != "running":
            raise AssertionError(f"detach worker was not left running: {detach_state}")
        detach_before = wait_for_json(detach_paths / "heartbeat.json")
        assert_heartbeat(detach_before, "detach-heartbeat-run", "detach-agent", {"running", "completed"})
        time.sleep(0.45)
        detach_after = wait_for_json(detach_paths / "heartbeat.json")
        if int(detach_after.get("sequence", 0)) <= int(detach_before.get("sequence", 0)) and detach_after.get("timestamp") == detach_before.get("timestamp"):
            raise AssertionError("detach slow heartbeat did not advance")
        wait_for_done(project, "detach-heartbeat-run", 1, profile)
        detach_final = wait_for_json(detach_paths / "heartbeat.json")
        assert_heartbeat(detach_final, "detach-heartbeat-run", "detach-agent", {"completed"})

        apply_plan(project, root, "supervisor-heartbeat-run", [worker_block("supervisor-agent", "slow-shell-agent")])
        first_tick = pf("supervisor", "tick", "--project-root", str(project), "--run", "supervisor-heartbeat-run", "--profile", str(profile))
        if "started=1" not in first_tick.stdout:
            raise AssertionError("supervisor did not start heartbeat worker")
        supervisor_paths = run_root(project, "supervisor-heartbeat-run", "supervisor-agent")
        supervisor_live = wait_for_json(supervisor_paths / "heartbeat.json")
        assert_heartbeat(supervisor_live, "supervisor-heartbeat-run", "supervisor-agent", {"running", "completed"})
        wait_for_done(project, "supervisor-heartbeat-run", 1, profile)
        supervisor_final = wait_for_json(supervisor_paths / "heartbeat.json")
        assert_heartbeat(supervisor_final, "supervisor-heartbeat-run", "supervisor-agent", {"completed"})

        apply_plan(project, root, "fail-heartbeat-run", [worker_block("failed-agent", "fail-shell-agent")])
        pf("worker-run", "start", "--project-root", str(project), "--task", "failed-agent", "--driver", "fail-shell-agent", "--wait", expect=1)
        fail_paths = run_root(project, "fail-heartbeat-run", "failed-agent")
        fail_heartbeat = wait_for_json(fail_paths / "heartbeat.json")
        assert_heartbeat(fail_heartbeat, "fail-heartbeat-run", "failed-agent", {"failed"})
        fail_exit = wait_for_json(fail_paths / "exit.json")
        if fail_exit.get("status") != "failed":
            raise AssertionError(f"failed worker exit artifact mismatch: {fail_exit}")
        pf("worker-run", "collect", "--project-root", str(project), "--task", "failed-agent", expect=1)

    print("PASS: shell-agent heartbeat contract smoke")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
