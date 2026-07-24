#!/usr/bin/env python3
"""Full smoke for shell-launched agents under the process supervisor."""

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
    (project / "README.md").write_text("# Full shell supervisor smoke\n", encoding="utf-8")
    pf("workplace-init", "--workplace", str(workplace), "--apply")
    pf("project-onboard", "--project-root", str(project), "--workplace", str(workplace), "--type", "generic-software-project", "--apply")
    return project


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
  variables:
    PF_WORKER_RUN_ID: "{{run_id}}"
    PF_WORKER_TASK_ID: "{{task_id}}"
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
    write_driver(driver_dir / "slow-shell-agent.yaml", "slow-shell-agent", "sleep", 10, 3.0)
    write_driver(driver_dir / "fail-shell-agent.yaml", "fail-shell-agent", "fail", 10)
    write_driver(driver_dir / "timeout-shell-agent.yaml", "timeout-shell-agent", "sleep", 1, 3.0)
    registry.write_text(
        """schema_version: 1
runtime_drivers:
  - id: slow-shell-agent
    path: runtime-drivers/slow-shell-agent.yaml
    status: available
  - id: fail-shell-agent
    path: runtime-drivers/fail-shell-agent.yaml
    status: available
  - id: timeout-shell-agent
    path: runtime-drivers/timeout-shell-agent.yaml
    status: available
""",
        encoding="utf-8",
    )


def write_profile(path: Path, max_parallel: int) -> None:
    path.write_text(
        f"""schema_version: 1
defaults:
  runtime_driver: test-shell-agent
  max_parallel_workers: {max_parallel}
scheduling:
  max_parallel_workers: {max_parallel}
loop:
  interval_seconds: 0.2
  max_ticks: 20
""",
        encoding="utf-8",
    )


def worker_block(task_id: str, driver: str, allowed: str, depends_on: str | None = None) -> str:
    dep = f"    depends_on: [{depends_on}]\n" if depends_on else ""
    return f"""  - id: {task_id}
    title: {task_id}
    role: test
    process: testing
    execution_mode: assurance
    writer: true
    allowed_files: [{allowed}]
    allowed_read_files: [.pf/contexts/project-context.snapshot.yaml]
    required_sources: [.pf/contexts/project-context.snapshot.yaml]
    required_outputs:
      - id: {task_id}-report
        path: .pf/artifacts/{task_id}-report.md
        type: markdown
        required: true
    expected_report_artifact: .pf/artifacts/{task_id}-report.md
    runtime_driver: {driver}
{dep}    worker_may_rebuild_context: false
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


def append_runtime_driver(project: Path, task_id: str, driver: str) -> None:
    assignment = project / ".pf/assignments" / f"{task_id}.yaml"
    text = assignment.read_text(encoding="utf-8")
    if "\nruntime_driver:" not in text:
        assignment.write_text(text.rstrip() + f"\nruntime_driver: {driver}\nworker_may_rebuild_context: false\n", encoding="utf-8")


def create_manual_task(project: Path, run_id: str, task_id: str, driver: str, allowed: str, force: bool = False, capsule_allowed: str | None = None) -> None:
    task_allowed = capsule_allowed or allowed
    args = [
        "task-create",
        "--project-root",
        str(project),
        "--run",
        run_id,
        "--id",
        task_id,
        "--title",
        task_id,
        "--process",
        "testing",
        "--allowed-file",
        task_allowed,
        "--allowed-read-file",
        ".pf/contexts/project-context.snapshot.yaml",
        "--required-source",
        ".pf/contexts/project-context.snapshot.yaml",
        "--required-output",
        f"id={task_id}-report,path=.pf/artifacts/{task_id}-report.md,type=markdown,required=true",
        "--expected-report-artifact",
        f".pf/artifacts/{task_id}-report.md",
        "--apply",
    ]
    if force:
        args.insert(-1, "--force-with-handoff")
    pf(*args)
    append_runtime_driver(project, task_id, driver)
    pf("project-context-refresh", "--project-root", str(project))
    pf("assignment-capsule", "--project-root", str(project), "--assignment", str(project / ".pf/assignments" / f"{task_id}.yaml"), "--force")
    pf("worker-launch-prompt", "create", "--project-root", str(project), "--task", task_id, "--apply")
    if capsule_allowed and capsule_allowed != allowed:
        assignment = project / ".pf/assignments" / f"{task_id}.yaml"
        assignment.write_text(assignment.read_text(encoding="utf-8").replace(capsule_allowed, allowed), encoding="utf-8")


def state(project: Path, run_id: str, task_id: str) -> dict[str, object]:
    return json.loads((project / f".pf/runtime/agent-runs/{run_id}/{task_id}/status.json").read_text(encoding="utf-8"))


def wait_for_json(path: Path, timeout_seconds: float = 3.0) -> dict[str, object]:
    deadline = time.perf_counter() + timeout_seconds
    while time.perf_counter() < deadline:
        if path.is_file():
            return json.loads(path.read_text(encoding="utf-8"))
        time.sleep(0.05)
    raise AssertionError(f"timed out waiting for JSON file: {path}")


def wait_for_done(project: Path, run_id: str, expected_done: int, profile: Path, ticks: int = 12) -> None:
    for _index in range(ticks):
        pf("supervisor", "tick", "--project-root", str(project), "--run", run_id, "--profile", str(profile))
        status = pf("run-status", "--project-root", str(project), "--run", run_id).stdout
        if f"TASKS: done={expected_done}" in status:
            return
        time.sleep(0.25)
    raise AssertionError(f"run {run_id} did not reach done={expected_done}")


def assert_runtime_artifacts(project: Path, run_id: str, task_id: str) -> None:
    run_root = project / f".pf/runtime/agent-runs/{run_id}/{task_id}"
    for name in ["status.json", "command.json", "process.json", "stdout.log", "stderr.log", "heartbeat.json", "exit.json"]:
        if not (run_root / name).is_file():
            raise AssertionError(f"missing runtime artifact for {task_id}: {name}")
    report = project / f".pf/artifacts/{task_id}-report.md"
    if not report.is_file():
        raise AssertionError(f"missing expected report for {task_id}")


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="pf-full-shell-supervisor-", ignore_cleanup_errors=True) as temp:
        root = Path(temp)
        project = make_project(root)
        install_local_drivers(project)
        profile = root / "supervisor-profile.yaml"
        write_profile(profile, 4)

        nonblocking_plan = root / "nonblocking-plan.yaml"
        write_plan(
            nonblocking_plan,
            "nonblocking-shell-run",
            [worker_block("slow-probe-agent", "slow-shell-agent", ".pf/artifacts/slow-probe-agent-report.md")],
        )
        pf("orchestrator-plan", "validate", "--project-root", str(project), "--plan", str(nonblocking_plan))
        pf("orchestrator-plan", "apply", "--project-root", str(project), "--plan", str(nonblocking_plan), "--apply")
        started = time.perf_counter()
        first_tick = pf("supervisor", "tick", "--project-root", str(project), "--run", "nonblocking-shell-run", "--profile", str(profile))
        elapsed = time.perf_counter() - started
        if elapsed > 1.5:
            raise AssertionError(f"supervisor tick blocked for {elapsed:.2f}s")
        if "started=1" not in first_tick.stdout:
            raise AssertionError("nonblocking supervisor tick did not start one worker")
        slow_state = state(project, "nonblocking-shell-run", "slow-probe-agent")
        if slow_state.get("status") != "running":
            raise AssertionError("slow worker was not left running after non-blocking tick")
        heartbeat_path = project / ".pf/runtime/agent-runs/nonblocking-shell-run/slow-probe-agent/heartbeat.json"
        heartbeat_before = wait_for_json(heartbeat_path)
        time.sleep(0.45)
        heartbeat_after = wait_for_json(heartbeat_path)
        if int(heartbeat_after.get("sequence", 0)) <= int(heartbeat_before.get("sequence", 0)):
            raise AssertionError("slow worker heartbeat did not advance while running")
        wait_for_done(project, "nonblocking-shell-run", 1, profile)
        assert_runtime_artifacts(project, "nonblocking-shell-run", "slow-probe-agent")

        success_plan = root / "success-plan.yaml"
        write_plan(
            success_plan,
            "full-shell-run",
            [
                worker_block("fast-success-agent", "test-shell-agent", ".pf/artifacts/fast-success-agent-report.md"),
                worker_block("parallel-agent-a", "test-shell-agent", ".pf/artifacts/parallel-agent-a-report.md"),
                worker_block("parallel-agent-b", "test-shell-agent", ".pf/artifacts/parallel-agent-b-report.md"),
                worker_block("dependent-agent", "test-shell-agent", ".pf/artifacts/dependent-agent-report.md", depends_on="fast-success-agent"),
                worker_block("env-isolation-agent", "test-shell-agent", ".pf/artifacts/env-isolation-agent-report.md"),
            ],
        )
        pf("orchestrator-plan", "validate", "--project-root", str(project), "--plan", str(success_plan))
        pf("orchestrator-plan", "apply", "--project-root", str(project), "--plan", str(success_plan), "--apply")
        wait_for_done(project, "full-shell-run", 5, profile)
        for task_id in [
            "fast-success-agent",
            "parallel-agent-a",
            "parallel-agent-b",
            "dependent-agent",
            "env-isolation-agent",
        ]:
            assert_runtime_artifacts(project, "full-shell-run", task_id)
        env_report = (project / ".pf/artifacts/env-isolation-agent-report.md").read_text(encoding="utf-8")
        if "- leak_keys: `0`" not in env_report:
            raise AssertionError("env isolation agent reported leaked parent environment")

        pf("run-create", "--project-root", str(project), "--id", "overlap-shell-run", "--title", "Overlap shell run", "--process", "task-batch-execution", "--apply")
        create_manual_task(project, "overlap-shell-run", "overlap-agent-a", "slow-shell-agent", ".pf/artifacts/overlap/**")
        create_manual_task(project, "overlap-shell-run", "overlap-agent-b", "test-shell-agent", ".pf/artifacts/overlap/**", capsule_allowed=".pf/artifacts/overlap-b-temp.md")
        overlap_tick = pf("supervisor", "tick", "--project-root", str(project), "--run", "overlap-shell-run", "--profile", str(profile))
        overlap_report = (project / ".pf/runtime/supervisor/last-tick-report.md").read_text(encoding="utf-8")
        if "overlap-agent-b" not in overlap_report or "blocked_overlap" not in overlap_report:
            raise AssertionError("supervisor did not report overlap-agent-b as overlap-blocked")
        if "started=1" not in overlap_tick.stdout:
            raise AssertionError("overlap tick did not start exactly one overlapping task")
        wait_for_done(project, "overlap-shell-run", 2, profile)
        assert_runtime_artifacts(project, "overlap-shell-run", "overlap-agent-a")
        assert_runtime_artifacts(project, "overlap-shell-run", "overlap-agent-b")

        fail_plan = root / "fail-plan.yaml"
        write_plan(fail_plan, "fail-shell-run", [worker_block("fail-agent", "fail-shell-agent", ".pf/artifacts/fail-agent-report.md")], default_driver="fail-shell-agent")
        pf("orchestrator-plan", "validate", "--project-root", str(project), "--plan", str(fail_plan))
        pf("orchestrator-plan", "apply", "--project-root", str(project), "--plan", str(fail_plan), "--apply")
        failed = pf("supervisor", "run", "--project-root", str(project), "--run", "fail-shell-run", "--profile", str(profile), "--max-ticks", "4", "--interval", "0.1", expect=1)
        if "failed=1" not in failed.stdout:
            raise AssertionError("supervisor did not propagate nonzero shell-agent failure")
        if state(project, "fail-shell-run", "fail-agent").get("status") != "failed":
            raise AssertionError("failed shell agent state is not failed")

        timeout_plan = root / "timeout-plan.yaml"
        write_plan(timeout_plan, "timeout-shell-run", [worker_block("timeout-agent", "timeout-shell-agent", ".pf/artifacts/timeout-agent-report.md")], default_driver="timeout-shell-agent")
        pf("orchestrator-plan", "validate", "--project-root", str(project), "--plan", str(timeout_plan))
        pf("orchestrator-plan", "apply", "--project-root", str(project), "--plan", str(timeout_plan), "--apply")
        timed_out = pf("supervisor", "run", "--project-root", str(project), "--run", "timeout-shell-run", "--profile", str(profile), "--max-ticks", "8", "--interval", "0.25", expect=1)
        if "failed=1" not in timed_out.stdout:
            raise AssertionError("supervisor did not propagate shell-agent timeout")
        if state(project, "timeout-shell-run", "timeout-agent").get("status") != "timed_out":
            raise AssertionError("timeout shell agent state is not timed_out")

    print("PASS: full shell agents supervisor smoke")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
