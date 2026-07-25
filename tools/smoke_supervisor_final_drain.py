#!/usr/bin/env python3
"""Regression smoke for supervisor run final drain of detached workers."""

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


def make_project(root: Path) -> Path:
    workplace = root / "workplace"
    project = root / "project"
    project.mkdir()
    (project / "README.md").write_text("# Supervisor final drain smoke\n", encoding="utf-8")
    pf("workplace-init", "--workplace", str(workplace), "--apply")
    pf("project-onboard", "--project-root", str(project), "--workplace", str(workplace), "--type", "generic-software-project", "--apply")
    install_fail_driver(project)
    return project


def install_fail_driver(project: Path) -> None:
    driver_dir = project / ".pf/runtime/registries/runtime-drivers"
    driver_dir.mkdir(parents=True, exist_ok=True)
    (driver_dir / "fail-shell-agent.yaml").write_text(
        """schema_version: 1
id: fail-shell-agent
title: Fail Shell Agent
kind: shell
command:
  executable: "{python_executable}"
  args:
    - "{processforge_root}/tools/test_agents/pf_shell_agent.py"
    - "--capsule"
    - "{capsule_path}"
    - "--worker-prompt"
    - "{worker_prompt_path}"
    - "--output"
    - "{expected_report_path}"
    - "--heartbeat"
    - "{heartbeat_path}"
    - "--mode"
    - "fail"
working_directory: "{project_root}"
environment:
  inherit: false
  variables: {}
io:
  stdin: none
  stdout: .pf/runtime/agent-runs/{run_id}/{task_id}/stdout.log
  stderr: .pf/runtime/agent-runs/{run_id}/{task_id}/stderr.log
heartbeat:
  mode: file
  path: .pf/runtime/agent-runs/{run_id}/{task_id}/heartbeat.json
  optional: false
limits:
  timeout_seconds: 10
  max_retries: 0
security:
  allow_shell: false
  require_explicit_executable: false
  allow_network: false
""",
        encoding="utf-8",
    )
    (project / ".pf/runtime/registries/runtime-drivers.local.yaml").write_text(
        """schema_version: 1
runtime_drivers:
  - id: fail-shell-agent
    path: runtime-drivers/fail-shell-agent.yaml
    status: available
""",
        encoding="utf-8",
    )


def worker_block(task_id: str, driver: str = "test-shell-agent", depends_on: str | None = None) -> str:
    dep = f"    depends_on: [{depends_on}]\n" if depends_on else ""
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


def runtime_json(project: Path, run_id: str, task_id: str, name: str) -> dict[str, object]:
    path = project / f".pf/runtime/agent-runs/{run_id}/{task_id}/{name}.json"
    if not path.is_file():
        raise AssertionError(f"missing runtime artifact: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def apply_plan(project: Path, plan: Path) -> None:
    pf("orchestrator-plan", "validate", "--project-root", str(project), "--plan", str(plan))
    pf("orchestrator-plan", "apply", "--project-root", str(project), "--plan", str(plan), "--apply")


def assert_success_drained(project: Path, run_id: str, task_id: str) -> None:
    status = runtime_json(project, run_id, task_id, "status")
    exit_data = runtime_json(project, run_id, task_id, "exit")
    heartbeat = runtime_json(project, run_id, task_id, "heartbeat")
    run_status = pf("run-status", "--project-root", str(project), "--run", run_id).stdout
    if status.get("status") != "completed" or status.get("exit_code") != 0:
        raise AssertionError(f"status.json was not drained to completed: {status}")
    if exit_data.get("status") != "completed" or exit_data.get("exit_code") != 0:
        raise AssertionError(f"exit.json did not preserve completed exit: {exit_data}")
    if heartbeat.get("status") != "completed":
        raise AssertionError(f"heartbeat.json did not record completed state: {heartbeat}")
    if "TASKS: done=1" not in run_status:
        raise AssertionError("run-status did not show done=1 after supervisor run final drain\n" + run_status)


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="pf-supervisor-final-drain-") as temp:
        root = Path(temp)
        project = make_project(root)

        success_plan = root / "success-plan.yaml"
        write_plan(success_plan, "drain-success-run", [worker_block("drain-agent")])
        apply_plan(project, success_plan)
        run = pf("supervisor", "run", "--project-root", str(project), "--run", "drain-success-run", "--max-ticks", "1", "--interval", "0", "--final-drain-timeout", "3")
        if "FINAL-DRAIN:" not in run.stdout:
            raise AssertionError("supervisor run did not report final drain\n" + run.stdout)
        assert_success_drained(project, "drain-success-run", "drain-agent")

        no_start_plan = root / "no-start-plan.yaml"
        write_plan(
            no_start_plan,
            "drain-no-start-run",
            [worker_block("first-agent"), worker_block("second-agent", depends_on="first-agent")],
        )
        apply_plan(project, no_start_plan)
        pf("supervisor", "run", "--project-root", str(project), "--run", "drain-no-start-run", "--max-ticks", "1", "--interval", "0", "--final-drain-timeout", "3")
        assert_success_drained(project, "drain-no-start-run", "first-agent")
        second_status_path = project / ".pf/runtime/agent-runs/drain-no-start-run/second-agent/status.json"
        if second_status_path.is_file():
            second_status = json.loads(second_status_path.read_text(encoding="utf-8"))
            if second_status.get("status") in {"running", "completed"}:
                raise AssertionError(f"final drain started a new dependent task: {second_status}")
        no_start_status = pf("run-status", "--project-root", str(project), "--run", "drain-no-start-run").stdout
        if "done=1" not in no_start_status or "open=1" not in no_start_status:
            raise AssertionError("no-start drain run did not leave dependent task open\n" + no_start_status)

        fail_plan = root / "fail-plan.yaml"
        write_plan(fail_plan, "drain-fail-run", [worker_block("fail-agent", "fail-shell-agent")], default_driver="fail-shell-agent")
        apply_plan(project, fail_plan)
        pf("supervisor", "run", "--project-root", str(project), "--run", "drain-fail-run", "--max-ticks", "1", "--interval", "0", "--final-drain-timeout", "3", expect=1)
        fail_status = runtime_json(project, "drain-fail-run", "fail-agent", "status")
        fail_exit = runtime_json(project, "drain-fail-run", "fail-agent", "exit")
        if fail_status.get("status") == "completed" or fail_exit.get("exit_code") == 0:
            raise AssertionError(f"failed detached worker was converted to success: status={fail_status} exit={fail_exit}")
        if fail_status.get("status") != "failed" or fail_exit.get("exit_code") != 7:
            raise AssertionError(f"failed detached worker did not preserve non-zero exit: status={fail_status} exit={fail_exit}")
        fail_run_status = pf("run-status", "--project-root", str(project), "--run", "drain-fail-run").stdout
        if "TASKS: failed=1" not in fail_run_status:
            raise AssertionError("failed detached worker did not synchronize task lifecycle\n" + fail_run_status)
        pf("supervisor", "tick", "--project-root", str(project), "--run", "drain-fail-run", expect=1)
        fail_status_after = runtime_json(project, "drain-fail-run", "fail-agent", "status")
        if fail_status_after.get("status") == "completed":
            raise AssertionError("manual tick converted failed detached worker to completed")

    print("PASS: supervisor final drain smoke")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
