#!/usr/bin/env python3
"""Real prepared-executor recovery and governed continuation in isolated fixtures."""
from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys
import tempfile

import processforge as core
from process_execution_smoke_support import fixture
from processforge_core.prepared_input import private_file
from processforge_core.process_execution import ProcessExecutionService
from smoke_garage_mode_not_promoted_by_session import call_mcp
from smoke_prepared_execution_context import (
    ROOT, RUN_ID, call, create_task, event_rows, make_shell_driver,
    pf, require, setup_basic_project,
)


def governed_continuation() -> None:
    with fixture() as (workplace, project, started):
        code, output = call(project, started["assignment_id"], "prepare", driver="manual")
        require(code != 0 and "worker_report_undeclared" in output, output)

        class ScopedFixtureService(ProcessExecutionService):
            def _write_capsule(self, run, assignment, pin):
                # Declare scope before immutable context creation. Do not rewrite
                # a persisted capsule or its pins to obtain a positive fixture.
                report = ".pf/artifacts/governed-worker.md"
                assignment.update(
                    allowed_files=[report], expected_report={"artifact": report},
                    required_outputs=[{"id": "worker-report", "path": report, "required": True}],
                )
                return super()._write_capsule(run, assignment, pin)

        objective = "Governed prepared executor recovery fixture"
        service = ScopedFixtureService(project, workplace, core)
        work = service.start(objective=objective, process_id="declarative-smoke")
        require(work["action"] == "created_new", work)
        task = work["assignment_id"]
        driver = make_shell_driver(project)
        code, output = call(project, task, "start", driver=str(driver))
        require(code == 0, output)
        paths = [core.assignment_yaml_path(project, task),
                 core.run_yaml_path(project, work["run_id"]),
                 core.assignment_capsule_path(project, task)]
        before = [path.read_bytes() for path in paths]
        for _ in range(2):
            code, output = call(project, task, "collect")
            require(code == 0, output)
        require(before == [path.read_bytes() for path in paths],
                "governed collection changed assignment/run/capsule")
        events = event_rows(project)
        require(sum(row["event_type"] == "worker.run.collected" for row in events) == 1, events)
        require(not any(row["event_type"] in {"task.completed", "assignment.completed"}
                        for row in events), "worker completed primary Work")

        # Each helper call starts and closes a new source stdio MCP process.
        # This proves durable reconnect in a fixture, not a connected host update.
        resumed = call_mcp(workplace, "pf.work.start", {
            "project_root": str(project), "objective": objective,
            "process_id": "declarative-smoke",
        })
        require(resumed.get("action") == "continue_existing"
                and resumed.get("run_id") == work["run_id"]
                and resumed.get("assignment_id") == task, resumed)
        current = call_mcp(workplace, "pf.work.state", {"project_root": str(project)})
        require(current["run"]["id"] == work["run_id"]
                and current["assignment"]["id"] == task
                and current["stage"]["id"] == "prepare", current)
        transitioned = call_mcp(workplace, "pf.work.transition", {
            "project_root": str(project), "outcome": "completed",
            "notes": "Collected executor result reviewed by fixture primary agent.",
            "evidence": [
                {"kind": "artifact", "artifact_id": "brief", "status": "ready",
                 "path": ".pf/artifacts/governed-worker.md"},
                {"kind": "gate", "gate_id": "prepare-ready", "status": "passed"},
            ],
        })
        require(transitioned.get("action") == "stage_transitioned"
                and transitioned["stage"]["id"] == "build", transitioned)
        continued = call_mcp(workplace, "pf.work.state", {"project_root": str(project)})
        require(continued["run"]["id"] == work["run_id"]
                and continued["assignment"]["id"] == task
                and continued["stage"]["id"] == "build", continued)
        require(paths[2].read_bytes() == before[2], "transition rewrote immutable capsule")
    print("PASS: offline governed execution, collection invariance, source MCP reconnect and transition", flush=True)


def abrupt_collection_recovery() -> None:
    with tempfile.TemporaryDirectory(prefix="pf-prepared-crash-") as raw:
        _, project = setup_basic_project(Path(raw), "crash-project")
        pf("run-create", "--project-root", str(project), "--id", RUN_ID,
           "--title", "Crash recovery fixture", "--process", "task-batch-execution", "--apply")
        create_task(project, "crash-task")
        code, output = call(project, "crash-task", "prepare", driver="manual")
        require(code == 0, output)
        (project / ".pf/artifacts/crash-task.md").write_text("# Crash recovery report\n", encoding="utf-8")
        child = '''import argparse,os,sys
sys.path.insert(0,sys.argv[1])
import processforge as core
from processforge_core import prepared_input
original=prepared_input.write_once
def interrupted(path,document):
    if path.name=='collection-complete.json': os._exit(77)
    return original(path,document)
prepared_input.write_once=interrupted
core.command_worker_run_collect(argparse.Namespace(project_root=sys.argv[2],task='crash-task'))
'''
        crashed = subprocess.run(
            [sys.executable, "-B", "-c", child, str(ROOT / "tools"), str(project)],
            capture_output=True, text=True, encoding="utf-8", timeout=90,
        )
        require(crashed.returncode == 77, (crashed.returncode, crashed.stdout, crashed.stderr))
        paths = core.worker_run_paths(project, RUN_ID, "crash-task")
        lock = paths["root"] / ".lifecycle.lock"
        state = core.json_read(paths["status"])
        attempt = (project / state["prepared_input"]["path"]).parent
        receipt = attempt / "collection-receipt.json"
        complete = attempt / "collection-complete.json"
        require(lock.is_file() and receipt.is_file() and not complete.exists(),
                "child did not leave the expected interrupted receipt/lock state")
        receipt_bytes = receipt.read_bytes()
        # Recover in another process, with no monkeypatch or in-memory state.
        for _ in range(2):
            pf("worker-run", "collect", "--project-root", str(project), "--task", "crash-task")
        require(not lock.exists() and complete.is_file() and receipt.read_bytes() == receipt_bytes,
                "dead-owner recovery lost receipt or completion")
        events = event_rows(project)
        for kind in ("task.completed", "assignment.completed", "worker.run.collected"):
            require(sum(row["event_type"] == kind for row in events) == 1,
                    {"kind": kind, "events": events})
    print("PASS: actual process death, dead-owner lock and exactly-once receipt recovery", flush=True)


def private_redirect_refused() -> None:
    with tempfile.TemporaryDirectory(prefix="pf-prepared-path-") as raw:
        project = Path(raw).resolve()
        agent = project / ".pf/runtime/agent-runs/path-run/path-task"
        target = project / ".pf/artifacts/public-fixture"
        agent.mkdir(parents=True)
        target.mkdir(parents=True)
        link = agent / "attempts"
        if os.name == "nt":
            def quote(value: Path) -> str:
                return "'" + str(value).replace("'", "''") + "'"
            command = "New-Item -ItemType Junction -Path " + quote(link) + " -Target " + quote(target) + " | Out-Null"
            created = subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command", command],
                                     capture_output=True, text=True, timeout=20)
            require(created.returncode == 0, created.stderr)
        else:
            link.symlink_to(target, target_is_directory=True)
        try:
            try:
                private_file(project, ".pf/runtime/agent-runs/path-run/path-task/attempts/1/prepared-input.json")
            except ValueError as exc:
                require(str(exc) == "prepared_path_redirected", str(exc))
            else:
                raise AssertionError("private manifest directory redirection accepted")
            require(not list(target.iterdir()), "private bytes were written through redirect")
        finally:
            # Verify both endpoints are inside this isolated fixture, then remove
            # only the link using one native filesystem API (never recurse).
            require(link.parent.resolve().is_relative_to(project)
                    and target.resolve().is_relative_to(project), "fixture cleanup escaped its root")
            if os.name == "nt":
                link.rmdir()
            else:
                link.unlink()
    print("PASS: real directory redirect refused without private-byte publication", flush=True)


def main() -> int:
    governed_continuation()
    abrupt_collection_recovery()
    private_redirect_refused()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
