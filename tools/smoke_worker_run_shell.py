#!/usr/bin/env python3
"""Regression smoke tests for `worker-run` lifecycle and inspector behavior."""

from __future__ import annotations

import json
import os
import shutil
import sys
import threading
import time
import uuid
from pathlib import Path
from typing import Any

from processforge_subprocess import CommandResult, diagnostic_text, run_command as run_processforge_command


ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "tools" / "processforge.py"


def pf(*args: str, expect: int | None = 0, timeout: int = 90) -> CommandResult:
    env = os.environ.copy()
    env["PF_LEAK_TEST_SECRET"] = "must-not-reach-worker"
    result = run_processforge_command([sys.executable, str(CLI), *args], cwd=ROOT, timeout=timeout, env=env)
    if result.timed_out:
        raise AssertionError("timeout: " + " ".join(args) + "\n" + diagnostic_text(result))
    if expect is not None and result.returncode != expect:
        raise AssertionError(f"expected {expect}, got {result.returncode}: {' '.join(args)}\n{diagnostic_text(result)}")
    return result


RUN_ID = "shell-run"


def make_temporary_root(prefix: str, parent: Path) -> Path:
    root = parent / f".{prefix}-{uuid.uuid4().hex}"
    root.mkdir()
    return root


def make_project(root: Path) -> Path:
    project = root / "project"
    workplace = root / "workplace"
    project.mkdir()
    (project / "README.md").write_text("# Shell worker smoke\n", encoding="utf-8")
    pf("workplace-init", "--workplace", str(workplace), "--apply")
    pf(
        "project-onboard",
        "--project-root",
        str(project),
        "--workplace",
        str(workplace),
        "--type",
        "generic-software-project",
        "--apply",
    )
    pf("run-create", "--project-root", str(project), "--id", RUN_ID, "--title", "Shell run", "--process", "task-batch-execution", "--apply")
    return project


def create_task(project: Path, task_id: str, *, title: str) -> None:
    report_artifact = f".pf/artifacts/{task_id}-report.md"
    allowed_file = report_artifact
    pf(
        "task-create",
        "--project-root",
        str(project),
        "--run",
        RUN_ID,
        "--id",
        task_id,
        "--title",
        title,
        "--process",
        "task-batch-execution",
        "--allowed-file",
        allowed_file,
        "--required-output",
        f"id={task_id}-report,path={report_artifact},type=markdown,required=true",
        "--expected-report-artifact",
        report_artifact,
        "--apply",
    )


def runtime_root(project: Path, task_id: str) -> Path:
    return project / ".pf" / "runtime" / "agent-runs" / RUN_ID / task_id


def status_path(project: Path, task_id: str) -> Path:
    return runtime_root(project, task_id) / "status.json"


def command_path(project: Path, task_id: str) -> Path:
    return runtime_root(project, task_id) / "command.json"


def marker_path(project: Path, task_id: str) -> Path:
    return runtime_root(project, task_id) / "start-pids.log"


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def wait_status(project: Path, task_id: str, expected_status: str, timeout_seconds: float = 8.0) -> dict[str, Any]:
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        state = read_json(status_path(project, task_id))
        if state.get("status") == expected_status:
            return state
        time.sleep(0.1)
    raise AssertionError(f"expected status={expected_status!r} for task={task_id}, got={state if 'state' in locals() else {}}")


def read_pid_markers(project: Path, task_id: str) -> list[int]:
    path = marker_path(project, task_id)
    if not path.is_file():
        return []
    values: list[int] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            values.append(int(line))
        except ValueError:
            continue
    return values


def stop_if_running(project: Path, task_id: str) -> None:
    state = read_json(status_path(project, task_id))
    if state.get("status") == "running":
        pf("worker-run", "stop", "--project-root", str(project), "--task", task_id, expect=None)
        deadline = time.time() + 8.0
        while time.time() < deadline:
            current = read_json(status_path(project, task_id)).get("status")
            if current != "running":
                return
            time.sleep(0.1)
        raise AssertionError(f"task {task_id} did not stop in cleanup window")


def ensure_stopped(project: Path, task_id: str) -> None:
    state = read_json(status_path(project, task_id))
    status = state.get("status")
    if status not in {"stopped", "completed", "failed", "timed_out", "unknown_exit", "lost", "cancelled", None, ""}:
        raise AssertionError(f"expected terminal state for {task_id}, got {status!r}")


def driver_yaml_path(
    project: Path,
    driver_id: str,
    *,
    sleep_seconds: int = 20,
    base_dir: Path | None = None,
    inherit_environment: bool = True,
    task_id_for_marker: str | None = None,
) -> Path:
    base_dir = base_dir or (project / ".pf" / "runtime" / "regression-drivers")
    marker_task = task_id_for_marker or "{task_id}"
    marker = str(Path(".pf/runtime/agent-runs") / RUN_ID / marker_task / "start-pids.log")
    script = (
        "import os, pathlib, time\n"
        f"path = pathlib.Path(r'{marker}')\n"
        "path.parent.mkdir(parents=True, exist_ok=True)\n"
        "with open(path, 'a', encoding='utf-8') as handle:\n"
        "    handle.write(str(os.getpid()) + '\\\\n')\n"
        f"time.sleep({sleep_seconds})\n"
    )
    path = base_dir / f"{driver_id}.yaml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(
            [
                "schema_version: 1",
                f"id: {driver_id}",
                "title: Regression Shell Driver",
                "kind: shell",
                "command:",
                "  executable: '{python_executable}'",
                "  args:",
                "    - '-c'",
                f"    - {json.dumps(script)}",
                "working_directory: '{project_root}'",
                "environment:",
                f"  inherit: {str(inherit_environment).lower()}",
                "  variables: {}",
                "io:",
                "  stdin: none",
                "  stdout: '.pf/runtime/agent-runs/{run_id}/{task_id}/stdout.log'",
                "  stderr: '.pf/runtime/agent-runs/{run_id}/{task_id}/stderr.log'",
                "heartbeat:",
                "  mode: file",
                "  path: '.pf/runtime/agent-runs/{run_id}/{task_id}/heartbeat.json'",
                "  optional: true",
                "limits:",
                "  timeout_seconds: 120",
                "  max_retries: 0",
                "security:",
                "  allow_shell: false",
                "  require_explicit_executable: false",
                "  allow_network: false",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    return path


def assert_single_output_contains(result: CommandResult, needle: str, task: str) -> None:
    if needle not in (result.stdout + result.stderr):
        raise AssertionError(f"task={task} expected {needle!r} in output\n{diagnostic_text(result)}")


def start_task(task_id: str, project: Path, *, driver: Path, expect: int = 0, detach: bool = True) -> CommandResult:
    args = [
        "worker-run",
        "start",
        "--project-root",
        str(project),
        "--task",
        task_id,
        "--driver",
        str(driver),
    ]
    if detach:
        args.append("--detach")
    return pf(*args, expect=expect, timeout=120)


def smoke_environment_isolation(project: Path) -> None:
    task_id = "env-isolation"
    create_task(project, task_id, title="Environment isolation")
    driver = driver_yaml_path(project, "regression-env-isolation", sleep_seconds=2, inherit_environment=False)
    report_path = project / ".pf/artifacts/env-isolation-report.md"

    start_task(task_id, project, driver=driver, detach=False)
    report_path.write_text("- leak_keys: `0`\n", encoding="utf-8")
    collect = pf("worker-run", "collect", "--project-root", str(project), "--task", task_id, expect=0)
    command = read_json(command_path(project, task_id))
    env = command["command"]["environment"]
    if "PF_LEAK_TEST_SECRET" in env:
        raise AssertionError("isolated worker command environment contains leaked parent variable")

    if "- leak_keys: `0`" not in report_path.read_text(encoding="utf-8"):
        raise AssertionError("shell worker report did not show leak key check")

    assignment_path = project / ".pf" / "assignments" / f"{task_id}.yaml"
    assignment_payload = assignment_path.read_text(encoding="utf-8")
    assignment_path.write_text(assignment_payload.rstrip() + "\n# stale-check\n", encoding="utf-8")

    stale = pf(
        "worker-run",
        "prepare",
        "--project-root",
        str(project),
        "--task",
        task_id,
        "--driver",
        "test-shell-agent",
        expect=1,
    )
    if "assignment capsule is stale" not in (stale.stdout + stale.stderr):
        raise AssertionError("stale assignment capsule prepare check is missing")


def smoke_duplicate_start_sequential(project: Path) -> str:
    task_id = "duplicate-start-seq"
    create_task(project, task_id, title="Duplicate start sequential")
    driver = driver_yaml_path(project, "regression-dup-shell-seq", sleep_seconds=20)

    first = start_task(task_id, project, driver=driver)
    first_state = wait_status(project, task_id, "running", timeout_seconds=10.0)
    if first_state.get("pid") is None:
        raise AssertionError("sequential duplicate start did not populate running pid")
    marker_before = len(read_pid_markers(project, task_id))

    second = start_task(task_id, project, driver=driver)
    assert_single_output_contains(second, "SKIPPED", "duplicate_start_sequential")

    second_state = read_json(status_path(project, task_id))
    if second_state.get("status") != "running":
        raise AssertionError(f"second sequential start changed status={second_state.get('status')}")
    if second_state.get("pid") != first_state.get("pid"):
        raise AssertionError("second sequential start replaced active pid")
    if len(read_pid_markers(project, task_id)) != marker_before:
        raise AssertionError("sequential duplicate start wrote extra start marker")

    return task_id


def smoke_duplicate_start_parallel(project: Path) -> str:
    task_id = "duplicate-start-par"
    create_task(project, task_id, title="Duplicate start parallel")
    driver = driver_yaml_path(project, "regression-dup-shell-par", sleep_seconds=20, task_id_for_marker=task_id)

    outputs: list[CommandResult] = []
    errors: list[BaseException] = []
    start_barrier = threading.Barrier(2)

    def run_once() -> None:
        try:
            start_barrier.wait(timeout=5)
            outputs.append(start_task(task_id, project, driver=driver))
        except Exception as exc:
            errors.append(exc)

    threads = [threading.Thread(target=run_once), threading.Thread(target=run_once)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    if errors:
        raise AssertionError(f"parallel duplicate start invocation failed: {errors}")

    state = wait_status(project, task_id, "running", timeout_seconds=10.0)
    if state.get("status") != "running":
        raise AssertionError(f"parallel duplicate start status={state.get('status')}")
    if len(outputs) != 2:
        raise AssertionError(f"parallel duplicate start captured {len(outputs)} start outcomes, expected 2")
    texts = [result.stdout + result.stderr for result in outputs]
    running_count = sum(1 for text in texts if "RUNNING:" in text)
    skipped_count = sum(1 for text in texts if "SKIPPED:" in text)
    marker_path_ = marker_path(project, task_id)
    marker_count = 0
    deadline = time.time() + 5.0
    while time.time() < deadline:
        if marker_path_.is_file():
            marker_count = len([line for line in marker_path_.read_text(encoding="utf-8").splitlines() if line.strip()])
        if marker_count == 1:
            break
        if marker_count > 1:
            break
        time.sleep(0.1)
    if running_count != 1:
        raise AssertionError(f"parallel duplicate start expected 1 RUNNING outcome, got {running_count}: outputs={texts}")
    if skipped_count != 1:
        raise AssertionError(f"parallel duplicate start expected 1 SKIPPED outcome, got {skipped_count}: outputs={texts}")
    if marker_count != 1:
        raise AssertionError(f"parallel duplicate start expected 1 marker, got {marker_count}")

    return task_id


def smoke_prepare_while_running(project: Path) -> str:
    task_id = "prepare-while-running"
    create_task(project, task_id, title="Prepare while running")
    driver = driver_yaml_path(project, "regression-prepare-shell", sleep_seconds=20)

    start_task(task_id, project, driver=driver)
    before_state = wait_status(project, task_id, "running", timeout_seconds=10.0)
    before_pid = before_state.get("pid")
    before_markers = len(read_pid_markers(project, task_id))

    prepare = pf(
        "worker-run",
        "prepare",
        "--project-root",
        str(project),
        "--task",
        task_id,
        "--driver",
        str(driver),
        expect=None,
    )
    if prepare.returncode not in {0, 1}:
        raise AssertionError(f"prepare while running returned unexpected code {prepare.returncode}")

    after_state = read_json(status_path(project, task_id))
    if after_state.get("status") != "running":
        raise AssertionError(f"prepare while running changed status to {after_state.get('status')}")
    if after_state.get("pid") != before_pid:
        raise AssertionError(f"prepare while running changed pid {before_pid} -> {after_state.get('pid')}")
    if len(read_pid_markers(project, task_id)) != before_markers:
        raise AssertionError("prepare while running added extra markers")

    return task_id


def smoke_direct_path_recovery(project: Path, *, driver_root: Path) -> str:
    direct_task = "direct-path-recovery"
    create_task(project, direct_task, title="Direct path recovery")

    direct_driver = driver_yaml_path(project, "direct-path-recovery-driver", sleep_seconds=20, base_dir=driver_root)

    start_task(direct_task, project, driver=direct_driver)
    wait_status(project, direct_task, "running", timeout_seconds=10.0)
    direct_status = read_json(status_path(project, direct_task))
    direct_command = read_json(command_path(project, direct_task))
    if not direct_status or not direct_command:
        raise AssertionError("direct-path: missing durable artifacts")

    # Force direct-path recovery by making state use missing driver_id and keeping direct driver_ref.
    direct_status["driver_id"] = "missing-direct-driver-id"
    direct_command["driver_ref"] = str(direct_driver)
    write_json(status_path(project, direct_task), direct_status)
    write_json(command_path(project, direct_task), direct_command)

    recovery_tick = pf("supervisor", "tick", "--project-root", str(project), "--run", RUN_ID, expect=None, timeout=120)
    output = recovery_tick.stdout + recovery_tick.stderr
    if "runtime driver not found" in output:
        raise AssertionError("direct-path recovery still failing with 'runtime driver not found'")

    return direct_task


def smoke_durable_exit_reconciliation(project: Path) -> str:
    task_id = "durable-exit-reconciliation"
    create_task(project, task_id, title="Durable exit reconciliation")
    report_path = project / f".pf/artifacts/{task_id}-report.md"
    exit_path = runtime_root(project, task_id) / "exit.json"
    driver_path = project / ".pf" / "runtime" / "regression-drivers" / "durable-exit-reconciliation.yaml"
    script = (
        "import json, pathlib\n"
        f"path = pathlib.Path(r'{exit_path}')\n"
        "path.parent.mkdir(parents=True, exist_ok=True)\n"
        "path.write_text(json.dumps({'schema_version': 1, 'exit_code': 0, 'status': 'completed'}) + '\\n', encoding='utf-8')\n"
    )
    driver_path.write_text(
        "\n".join(
            [
                "schema_version: 1",
                "id: durable-exit-reconciliation",
                "title: Durable Exit Reconciliation Driver",
                "kind: shell",
                "command:",
                "  executable: '{python_executable}'",
                "  args:",
                "    - '-c'",
                f"    - {json.dumps(script)}",
                "working_directory: '{project_root}'",
                "environment:",
                "  inherit: false",
                "  variables: {}",
                "io:",
                "  stdin: none",
                "  stdout: '.pf/runtime/agent-runs/{run_id}/{task_id}/stdout.log'",
                "  stderr: '.pf/runtime/agent-runs/{run_id}/{task_id}/stderr.log'",
                "heartbeat:",
                "  mode: file",
                "  path: '.pf/runtime/agent-runs/{run_id}/{task_id}/heartbeat.json'",
                "  optional: true",
                "limits:",
                "  timeout_seconds: 30",
                "  max_retries: 0",
                "security:",
                "  allow_shell: false",
                "  require_explicit_executable: false",
                "  allow_network: false",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    start_task(task_id, project, driver=driver_path)
    deadline = time.time() + 8.0
    while time.time() < deadline:
        if exit_path.is_file():
            break
        time.sleep(0.1)
    if not exit_path.is_file():
        raise AssertionError("detached worker did not write its durable exit contract")

    status = pf("worker-run", "status", "--project-root", str(project), "--task", task_id, expect=0)
    if "status: completed" not in (status.stdout + status.stderr):
        raise AssertionError("worker-run status did not reconcile the durable exit contract")
    reconciled = read_json(status_path(project, task_id))
    if reconciled.get("status") != "completed" or reconciled.get("exit_code") != 0:
        raise AssertionError(f"unexpected reconciled state: {reconciled}")

    report_path.write_text("- durable exit: `collected`\n", encoding="utf-8")
    collect = pf("worker-run", "collect", "--project-root", str(project), "--task", task_id, expect=0)
    if "DONE:" not in (collect.stdout + collect.stderr):
        raise AssertionError("worker-run collect did not finish a reconciled worker")
    return task_id


def main() -> int:
    tasks_for_cleanup: list[str] = []
    temp_parent = ROOT / ".pf" / "tmp"
    temp_parent.mkdir(parents=True, exist_ok=True)
    temp_root = make_temporary_root("pf-worker-shell", temp_parent)
    driver_root = make_temporary_root("pf-worker-shell-driver", temp_parent)
    project = None
    try:
        project = make_project(temp_root)

        smoke_environment_isolation(project)
        tasks_for_cleanup.append("env-isolation")

        tasks_for_cleanup.append(smoke_duplicate_start_sequential(project))
        tasks_for_cleanup.append(smoke_duplicate_start_parallel(project))
        tasks_for_cleanup.append(smoke_prepare_while_running(project))
        tasks_for_cleanup.append(smoke_direct_path_recovery(project, driver_root=driver_root))
        tasks_for_cleanup.append(smoke_durable_exit_reconciliation(project))
    finally:
        if project is not None:
            for task_id in tasks_for_cleanup:
                stop_if_running(project, task_id)
                ensure_stopped(project, task_id)
        shutil.rmtree(temp_root, ignore_errors=True)
        shutil.rmtree(driver_root, ignore_errors=True)

    print("PASS: worker-run shell regressions smoke")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
