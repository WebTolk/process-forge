#!/usr/bin/env python3
"""Combined smoke for shell-launched agent proofs and supervisor failure semantics."""

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
    (project / "README.md").write_text("# Shell-launched agents smoke\n", encoding="utf-8")
    pf("workplace-init", "--workplace", str(workplace), "--apply")
    pf("project-onboard", "--project-root", str(project), "--workplace", str(workplace), "--type", "generic-software-project", "--apply")
    return project


def write_plan(path: Path, run_id: str, task_id: str, driver: str) -> None:
    path.write_text(
        f"""schema_version: 1
run:
  id: {run_id}
  title: {run_id}
  process: multi-agent-task-orchestration
orchestrator:
  role: orchestrator
runtime:
  default_driver: {driver}
  supervisor_profile: default
  start_policy: supervisor
workers:
  - id: {task_id}
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
integration:
  required: false
  role: orchestrator
  expected_output: .pf/artifacts/integration-report.md
""",
        encoding="utf-8",
    )


def tail(path: Path, limit: int = 1200) -> str:
    if not path.is_file():
        return "<missing>"
    text = path.read_text(encoding="utf-8", errors="replace")
    return text[-limit:]


def runtime_diagnostics(run_root: Path, expected: Path) -> str:
    existing = []
    if run_root.is_dir():
        existing = sorted(str(path.relative_to(run_root)) for path in run_root.rglob("*") if path.is_file())
    return "\n".join(
        [
            "FAIL: missing heartbeat.json",
            "",
            "Expected:",
            f"  {expected}",
            "",
            "Existing files:",
            "  " + ("\n  ".join(existing) if existing else "<none>"),
            "",
            "stdout tail:",
            tail(run_root / "stdout.log"),
            "",
            "stderr tail:",
            tail(run_root / "stderr.log"),
            "",
            "process.json:",
            tail(run_root / "process.json"),
            "",
            "command.json:",
            tail(run_root / "command.json"),
            "",
            "exit.json:",
            tail(run_root / "exit.json"),
        ]
    )


def wait_for_json(path: Path, run_root: Path, timeout_seconds: float = 5.0) -> dict[str, object]:
    deadline = time.perf_counter() + timeout_seconds
    last_error: Exception | None = None
    while time.perf_counter() < deadline:
        if path.is_file():
            try:
                return json.loads(path.read_text(encoding="utf-8"))
            except json.JSONDecodeError as exc:
                last_error = exc
        time.sleep(0.1)
    diagnostics = runtime_diagnostics(run_root, path)
    if last_error:
        diagnostics += f"\n\nLast JSON error: {last_error}"
    raise AssertionError(diagnostics)


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="pf-shell-supervisor-fix-") as temp:
        root = Path(temp)
        project = make_project(root)
        success_plan = root / "success-plan.yaml"
        write_plan(success_plan, "agent-proof-run", "proof-agent", "test-shell-agent")
        pf("orchestrator-plan", "validate", "--project-root", str(project), "--plan", str(success_plan))
        pf("orchestrator-plan", "apply", "--project-root", str(project), "--plan", str(success_plan), "--apply")
        pf("supervisor", "run", "--project-root", str(project), "--run", "agent-proof-run", "--max-ticks", "3", "--interval", "0")
        run_root = project / ".pf/runtime/agent-runs/agent-proof-run/proof-agent"
        process = wait_for_json(run_root / "process.json", run_root)
        command = wait_for_json(run_root / "command.json", run_root)
        heartbeat = wait_for_json(run_root / "heartbeat.json", run_root)
        stdout = (run_root / "stdout.log").read_text(encoding="utf-8")
        report = (project / ".pf/artifacts/proof-agent-report.md").read_text(encoding="utf-8")
        if not isinstance(process.get("pid"), int) or process["pid"] <= 0:
            raise AssertionError("process proof missing valid pid")
        if "pf_shell_agent.started" not in stdout or "pf_shell_agent.completed" not in stdout:
            raise AssertionError("stdout proof missing shell-agent lifecycle events")
        if heartbeat.get("pid") != process.get("pid"):
            raise AssertionError("heartbeat pid does not match process proof")
        if heartbeat.get("run_id") != "agent-proof-run" or heartbeat.get("task_id") != "proof-agent":
            raise AssertionError("heartbeat run/task identity does not match proof run")
        if heartbeat.get("status") not in {"running", "completed"}:
            raise AssertionError("heartbeat status is not a live/completed proof status")
        if "PF_LEAK_TEST_SECRET" in command["command"]["environment"] or "- leak_keys: `0`" not in report:
            raise AssertionError("environment isolation proof failed")

        failing_plan = root / "failing-plan.yaml"
        write_plan(failing_plan, "agent-fail-run", "failed-agent", "generic-shell")
        pf("orchestrator-plan", "validate", "--project-root", str(project), "--plan", str(failing_plan))
        pf("orchestrator-plan", "apply", "--project-root", str(project), "--plan", str(failing_plan), "--apply")
        failed = pf("supervisor", "run", "--project-root", str(project), "--run", "agent-fail-run", "--max-ticks", "1", "--interval", "0", expect=1)
        if "failed=1" not in failed.stdout:
            raise AssertionError("supervisor run did not propagate worker start failure")
    print("PASS: shell-launched agents supervisor fix smoke")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
