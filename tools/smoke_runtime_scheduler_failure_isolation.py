#!/usr/bin/env python3
"""Exercise real Runtime scheduling across corrupt cache and missing assignments."""
from __future__ import annotations

import tempfile
import threading
import time
from pathlib import Path

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
    print("PASS: real scheduler isolates malformed cache/missing assignment, recovers, and exposes dead threads")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
