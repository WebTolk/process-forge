#!/usr/bin/env python3
"""Negotiated server stop and actual authenticated HTTP admission guards."""
from __future__ import annotations
import argparse
from contextlib import redirect_stdout
from http.server import ThreadingHTTPServer
import io
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import threading
import time
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import processforge as core
from pf_runtime import service


def put(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")


def wait_until(predicate, timeout=3):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return True
        threading.Event().wait(0.01)
    return False


def main():
    with tempfile.TemporaryDirectory(prefix="pf-server spaces-") as temp:
        root = Path(temp)
        wp, project = root / "workplace", root / "project"
        put(project / ".pf/process-forge.yaml", {})
        cache_path = wp / "runtime/pf-runtime-host/state.json"
        put(cache_path, {"projects": [{"project_root": str(project)}], "sessions": {}})
        worker = project / ".pf/runtime/agent-runs/task/attempt/status.json"
        runtime = service.RuntimeProcess(wp, core, interval=2)
        runtime.state.update(status="ready", health="ready")
        handler_finished = threading.Event()
        base_handler = runtime.make_handler()
        class ObservedHandler(base_handler):
            def do_POST(self):
                try:
                    super().do_POST()
                finally:
                    if self.path == "/event":
                        handler_finished.set()
        server = ThreadingHTTPServer(("127.0.0.1", 0), ObservedHandler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        endpoint = f"http://127.0.0.1:{server.server_port}"
        guarded = dict(require_idle=True, expected_instance_id=runtime.instance_id)
        post = lambda path, payload, token=runtime.token: service.http_json("POST", endpoint + path, token, payload)
        try:
            assert post("/shutdown", guarded, "wrong")[0] == 401
            assert post("/shutdown", {**guarded, "expected_instance_id": "old"})[0] == 409
            put(worker, {"status": "running"})
            assert post("/shutdown", guarded)[0] == 409 and not runtime.stop_event.is_set()
            put(worker, {"status": "completed"})
            cache_path.write_text("invalid")
            assert post("/shutdown", guarded)[0] == 409
            put(cache_path, {"projects": [{"project_root": str(project)}], "sessions": {}})
            entered, release = threading.Event(), threading.Event()
            def slow_event(*args, **kwargs):
                entered.set()
                assert release.wait(5)
                return {"ok": True}
            responses = []
            with patch.object(service.host, "ingest_event", slow_event):
                request = threading.Thread(target=lambda: responses.append(post("/event", {})), daemon=True)
                request.start()
                assert entered.wait(3)
                assert runtime.active_requests == 1
                assert post("/shutdown", guarded)[0] == 409
                assert runtime.state["status"] == "ready"
                release.set()
                request.join(4)
            # Receiving the response is earlier than the server's finally block.
            assert handler_finished.wait(3)
            assert responses[0][0] == 200 and runtime.active_requests == 0
            runtime.scheduler_active = True
            assert post("/shutdown", guarded)[0] == 409
            runtime.scheduler_active = False
            observed, finish = threading.Event(), threading.Event()
            def held_guard(*args):
                observed.set()
                assert finish.wait(5)
                return {"counts": {"running": 1}}
            with patch.object(service.metrics_core(), "shutdown_workers", held_guard):
                shutdown_response = []
                shutdown_request = threading.Thread(target=lambda: shutdown_response.append(post("/shutdown", guarded)), daemon=True)
                shutdown_request.start()
                assert observed.wait(3)
                assert post("/event", {})[0] == 503
                assert post("/shutdown", guarded)[0] == 409
                finish.set()
                shutdown_request.join(4)
                assert shutdown_response[0][0] == 409 and wait_until(lambda: not runtime.shutdown_check)
            assert post("/shutdown", guarded)[0] == 200 and runtime.stop_event.wait(3)
            assert post("/event", {})[0] == 503
            # Explicit legacy/force request retains compatibility, despite busy records.
            runtime.state["status"] = "ready"
            runtime.stop_event.clear()
            put(worker, {"status": "running"})
            assert post("/shutdown", {})[0] == 200 and runtime.stop_event.wait(3)
        finally:
            server.shutdown()
            server.server_close()
            thread.join(3)
        args = argparse.Namespace(command="server", workplace=str(wp), force=False, timeout=1)
        inspection = {"kind": "ready", "state": {"pid": 1, "endpoint": endpoint, "instance_id": "owner"}, "pid": 1}
        with patch.object(core, "resolve_workplace_root", return_value=wp), patch.object(service, "inspect_lifecycle", return_value=inspection), patch.object(service, "http_json") as call:
            try:
                service.command_stop(args, core)
            except SystemExit as exc:
                assert "lacks guarded" in str(exc)
            else:
                raise AssertionError("old service received unsafe fallback")
            call.assert_not_called()
        with patch.object(core, "resolve_workplace_root", return_value=wp), patch.object(service, "inspect_lifecycle", return_value=inspection), patch.object(service, "http_json", return_value=(200, {})) as call, patch.object(core, "process_pid_running", return_value=False), patch.object(service, "cleanup_stale_runtime"):
            inspection["state"]["capabilities"] = {"guarded_shutdown": 1}
            with redirect_stdout(io.StringIO()):
                assert service.command_stop(args, core) == 0
            assert call.call_args.kwargs["payload"] == {"require_idle": True, "expected_instance_id": "owner"}
            args.force = True
            with redirect_stdout(io.StringIO()):
                assert service.command_stop(args, core) == 0
            assert call.call_args.kwargs["payload"] == {}
        missing = root / "does not exist"
        result = subprocess.run([sys.executable, "-B", str(ROOT / "bin/pf-server.py"), "status", "--workplace", str(missing), "--json"], capture_output=True, timeout=30)
        assert result.returncode == 0, result.stderr
        assert json.loads(result.stdout)["runtime"]["lifecycle"] == "not_running" and not missing.exists()
        # Both launcher and quoted arguments live in paths with spaces.
        fixture = root / "quoted launcher"
        (fixture / "bin").mkdir(parents=True)
        (fixture / "tools").mkdir()
        for name in ("pf.py", "pf-server.py"):
            shutil.copyfile(ROOT / "bin" / name, fixture / "bin" / name)
        (fixture / "tools/processforge.py").write_text("import json,sys; print(json.dumps(sys.argv[1:]))")
        result = subprocess.run([sys.executable, "-B", str(fixture / "bin/pf-server.py"), "status", "--workplace", str(missing), "--json"], capture_output=True, timeout=30)
        assert json.loads(result.stdout) == ["server", "status", "--workplace", str(missing), "--json"]
        parsed = core.build_parser().parse_args(["server", "run", "--workplace", str(wp), "--console"])
        assert parsed.func is core.command_runtime_serve and parsed.console
    print("PASS: actual HTTP busy/unknown/inflight/owner/auth guards, force, old capability refusal, launcher and readonly JSON")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
