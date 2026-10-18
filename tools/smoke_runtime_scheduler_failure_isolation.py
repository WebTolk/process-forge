#!/usr/bin/env python3
"""Exercise real Runtime scheduling across corrupt cache and missing assignments."""
from __future__ import annotations

import argparse
import contextlib
import io
import json
import tempfile
import threading
import time
from pathlib import Path
from unittest.mock import patch

import processforge as core
from pf_runtime import host, service


def wait_for(predicate, timeout: float = 8.0) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return
        time.sleep(0.025)
    raise AssertionError("scheduler did not make expected progress")


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="pf-runtime-isolation-") as raw:
        root = Path(raw)
        workplace = root / "workplace"
        core.write_yaml_file(workplace / "workplace.yaml", {
            "schema_version": 1, "id": "fixture-workplace",
            "coordination": {"default_project_mode": "simple", "director_enabled": False},
        })
        projects = [root / "bad-project", root / "good-project"]
        state = host.load_state(workplace)
        for project in projects:
            core.write_yaml_file(project / ".pf/process-forge.yaml", {
                "schema_version": 1, "project": {"id": project.name},
                "coordination": {"mode": "simple"},
                "paths": {"runtime": "runtime", "assignments": "assignments"},
            })
            host.remember_project(state, host.route_project(str(project), workplace, core))
        host.save_state(workplace, state, core)
        valid_cache = host.state_path(workplace).read_bytes()
        bad_run = projects[0] / ".pf/runs/broken/run.yaml"
        core.write_yaml_file(bad_run, {
            "id": "broken", "status": "in_progress", "tasks": [{"id": "missing"}],
        })
        runtime = service.RuntimeProcess(workplace, core, interval=0.25)
        runtime.state.update(status="ready", health="degraded")
        assert runtime.status_payload()["health"] == "degraded", "explicit health was hidden"
        runtime.state["health"] = "ready"
        host.state_path(workplace).write_text("{ malformed", encoding="utf-8")
        escaped = []

        def run():
            try:
                runtime.scheduler_loop()
            except BaseException as exc:
                escaped.append(type(exc).__name__)

        thread = threading.Thread(target=run, daemon=True)
        thread.start()
        try:
            wait_for(lambda: bool(runtime.state.get("last_scheduler_error")) or escaped)
            assert not escaped and thread.is_alive(), escaped
            assert runtime.status_payload()["health"] == "degraded"
            host.state_path(workplace).write_bytes(valid_cache)
            wait_for(lambda: "missing" in str(runtime.state.get("last_scheduler_error")))
            payload = runtime.state["last_scheduler_result"]
            assert any(item.get("project_id") == "good-project" for item in payload["projects"]), payload
            assert thread.is_alive() and not escaped, escaped
            assert runtime.status_payload()["health"] == "degraded"
            core.write_yaml_file(bad_run, {"id": "broken", "status": "in_progress", "tasks": []})
            wait_for(lambda: runtime.status_payload()["health"] == "ready")
            payload = runtime.state["last_scheduler_result"]
            assert {item["project_id"] for item in payload["projects"]} == {p.name for p in projects}, payload
            assert runtime.status_payload()["scheduler_alive"] is True
            # Real terminal worker evidence must remain a task failure while
            # a successful observation leaves the scheduler operational.
            task_id = "old-failed-worker"
            assignment = projects[0] / f".pf/assignments/{task_id}.yaml"
            core.write_yaml_file(assignment, {"id": task_id, "run_id": "broken", "status": "failed"})
            worker_status = core.worker_run_paths(projects[0], "broken", task_id)["status"]
            worker_status.parent.mkdir(parents=True, exist_ok=True)
            worker_status.write_text(json.dumps({"status": "failed", "driver_id": "manual", "failure_reason": "fixture failure"}), encoding="utf-8")
            core.write_yaml_file(bad_run, {"id": "broken", "status": "in_progress", "tasks": [{"id": task_id}]})
            before = (assignment.read_bytes(), worker_status.read_bytes())
            wait_for(lambda: any(task_id in row.get("inspector_result", {}).get("failed", []) for row in runtime.state["last_scheduler_result"]["projects"]))
            assert runtime.status_payload()["health"] == "ready", runtime.state
            assert all(runtime.state["scheduler"]["jobs"][job]["last_result"] == "ok" for job in ("director", "inspector", "projection"))
            with contextlib.redirect_stdout(io.StringIO()):
                assert core.command_supervisor_tick(argparse.Namespace(project_root=str(projects[0]), run="broken", profile=None, start_allowed=False)) == 1
                tick, code = host.tick_payload(workplace, [projects[0]], core, inspector=True)
            assert code == 1 and tick["status"] == "failed" and tick["scheduler_status"] == "ok", tick
            assert tick["projects"][0]["inspector_result"]["failed"] == [task_id], tick
            assert before == (assignment.read_bytes(), worker_status.read_bytes())
            # A genuine Director failure must still degrade even with valid
            # structured Inspector metadata; restoration must recover health.
            core.write_yaml_file(workplace / "workplace.yaml", {
                "schema_version": 1, "id": "fixture-workplace",
                "coordination": {"default_project_mode": "simple", "director_enabled": True},
            })
            manifest = projects[0] / ".pf/process-forge.yaml"
            configuration = core.read_yaml_file(manifest)
            configuration["coordination"]["mode"] = "organized"
            core.write_yaml_file(manifest, configuration)
            with patch.object(core, "command_agent_director_tick", return_value=1):
                wait_for(lambda: runtime.status_payload()["health"] == "degraded")
            wait_for(lambda: runtime.status_payload()["health"] == "ready")
            original_tick = host.tick_payload
            try:
                host.tick_payload = lambda *_args, **_kwargs: ({"projects": []}, 1)
                wait_for(lambda: runtime.status_payload()["health"] == "degraded")
            finally:
                host.tick_payload = original_tick
            wait_for(lambda: runtime.status_payload()["health"] == "ready")
        finally:
            runtime.stop_event.set()
            thread.join(timeout=3)
        assert not thread.is_alive() and not escaped, escaped
        stopped = runtime.status_payload()
        assert stopped["scheduler_alive"] is False and stopped["health"] == "degraded", stopped
    print("PASS: scheduler separates preserved task failures, isolates operational faults, recovers, and exposes dead threads")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
