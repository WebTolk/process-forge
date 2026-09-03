#!/usr/bin/env python3
"""Smoke test for the long-lived local PF Runtime process."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import http.client
import json
import os
import signal
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from processforge_subprocess import CommandResult, diagnostic_text, run_command as run_processforge_command
from pf_runtime.raw_ingress_kernel import _strip_windows_extended_prefix


ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "tools" / "processforge.py"


def pf(*args: str, expect: int = 0, timeout: int = 120) -> CommandResult:
    result = run_processforge_command([sys.executable, str(CLI), *args], cwd=ROOT, timeout=timeout)
    if result.timed_out:
        raise AssertionError("timeout: " + " ".join(args) + "\n" + diagnostic_text(result))
    if result.returncode != expect:
        raise AssertionError(f"expected {expect}, got {result.returncode}: {' '.join(args)}\n{diagnostic_text(result)}")
    return result


def runtime_dir(workplace: Path) -> Path:
    return workplace / "runtime" / "pf-runtime"


def service_state(workplace: Path) -> dict[str, object]:
    return json.loads((runtime_dir(workplace) / "service.json").read_text(encoding="utf-8"))


def token(workplace: Path) -> str:
    return str(json.loads((runtime_dir(workplace) / "token.json").read_text(encoding="utf-8"))["token"])


def http_json(method: str, url: str, *, bearer: str | None = None, payload: dict[str, object] | bytes | None = None) -> tuple[int, dict[str, object]]:
    if isinstance(payload, bytes):
        body = payload
    else:
        body = json.dumps(payload or {}, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(url, data=body if method != "GET" else None, method=method)
    request.add_header("Content-Type", "application/json")
    if bearer:
        request.add_header("Authorization", f"Bearer {bearer}")
    try:
        with urllib.request.urlopen(request, timeout=5.0) as response:
            text = response.read().decode("utf-8")
            return response.status, json.loads(text) if text.strip() else {}
    except urllib.error.HTTPError as exc:
        try:
            text = exc.read().decode("utf-8", errors="replace")
        except OSError:
            return exc.code, {"error": "connection closed while reading error response"}
        try:
            return exc.code, json.loads(text) if text.strip() else {}
        except json.JSONDecodeError:
            return exc.code, {"error": text}


def declared_oversized_request(endpoint: str, bearer: str) -> tuple[int, dict[str, object]]:
    """Assert header-based body rejection without racing a Windows socket close.

    The Runtime must reject requests above its declared body limit before it
    reads the body.  Sending only headers makes that contract deterministic on
    Windows, where a client still streaming megabytes can receive WSAECONNABORTED
    while the server is already returning the rejection.
    """
    parsed = urllib.parse.urlsplit(endpoint)
    connection = http.client.HTTPConnection(parsed.hostname, parsed.port, timeout=5.0)
    try:
        connection.putrequest("POST", "/event")
        connection.putheader("Authorization", f"Bearer {bearer}")
        connection.putheader("Content-Type", "application/json")
        connection.putheader("Content-Length", str(1024 * 1024 + 1))
        connection.endheaders()
        response = connection.getresponse()
        text = response.read().decode("utf-8", errors="replace")
        return response.status, json.loads(text) if text.strip() else {}
    finally:
        connection.close()


def kill_pid(pid: int) -> None:
    if os.name == "nt":
        subprocess.run(["taskkill", "/PID", str(pid), "/T", "/F"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
    else:
        os.kill(pid, signal.SIGKILL)
    deadline = time.monotonic() + 5.0
    while time.monotonic() < deadline:
        if os.name == "nt":
            probe = subprocess.run(["tasklist", "/FI", f"PID eq {pid}"], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, check=False)
            if str(pid) not in probe.stdout:
                return
        else:
            try:
                os.kill(pid, 0)
            except OSError:
                return
        time.sleep(0.1)


def make_project(root: Path, name: str, workplace: Path, mode: str) -> Path:
    project = root / name
    project.mkdir()
    (project / "README.md").write_text(f"# {name}\n", encoding="utf-8")
    pf("project-onboard", "--project-root", str(project), "--workplace", str(workplace), "--type", "generic-software-project", "--apply")
    pf("project-mode", "set", "--project-root", str(project), "--workplace", str(workplace), "--mode", mode)
    return project


def write_event(path: Path, payload: dict[str, object]) -> Path:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def start_runtime(workplace: Path) -> dict[str, object]:
    return json.loads(pf("runtime", "start", "--workplace", str(workplace), "--interval", "60", "--json").stdout)


def stop_runtime(workplace: Path) -> None:
    pf("runtime", "stop", "--workplace", str(workplace), timeout=30)


def assert_runtime_ready(workplace: Path) -> dict[str, object]:
    status = json.loads(pf("runtime", "status", "--workplace", str(workplace), "--json").stdout)
    if status.get("status") != "ready" or status.get("health") != "ready":
        raise AssertionError(f"runtime is not ready: {status}")
    return status


def main() -> int:
    # public-cleanliness: allow-private-path-fixture
    extended_drive = r"\\?\C:\fixture\runtime"
    # public-cleanliness: allow-private-path-fixture
    normal_drive = r"C:\fixture\runtime"
    if _strip_windows_extended_prefix(extended_drive) != normal_drive:
        raise AssertionError("Win32 extended drive path normalization failed")
    if _strip_windows_extended_prefix(r"\\?\UNC\server\share\runtime") != r"\\server\share\runtime":
        raise AssertionError("Win32 extended UNC path normalization failed")
    with tempfile.TemporaryDirectory(prefix="pf-long-lived-runtime-", ignore_cleanup_errors=True) as temp:
        root = Path(temp)
        workplace = root / "workplace"
        runtime_started = False
        pf("workplace-init", "--workplace", str(workplace), "--apply")
        pf("workplace-mode", "set", "--workplace", str(workplace), "--director-enabled", "true", "--director-office-enabled", "true")
        project_a = make_project(root, "project-a", workplace, "organized")
        project_b = make_project(root, "project-b", workplace, "simple")

        try:
            first = start_runtime(workplace)
            runtime_started = True
            second = start_runtime(workplace)
            if first.get("pid") != second.get("pid") or second.get("status") != "already_running":
                raise AssertionError(f"singleton start did not reuse active runtime: first={first} second={second}")

            initial_service = service_state(workplace)
            initial_lock = json.loads((runtime_dir(workplace) / "runtime.lock").read_text(encoding="utf-8"))
            if not initial_service.get("instance_id") or initial_service.get("instance_id") != initial_lock.get("instance_id"):
                raise AssertionError("ready runtime lock and service state do not share one instance_id")
            (runtime_dir(workplace) / "runtime.lock").unlink()
            orphaned_start = pf("runtime", "start", "--workplace", str(workplace), expect=1)
            if "requires stop/recovery" not in (orphaned_start.stdout + orphaned_start.stderr):
                raise AssertionError(f"orphaned live runtime allowed a second start: {diagnostic_text(orphaned_start)}")
            stop_runtime(workplace)
            runtime_started = False
            first = start_runtime(workplace)
            runtime_started = True
            if first.get("status") != "started":
                raise AssertionError(f"orphaned runtime did not stop and restart cleanly: {first}")
            initial_service = service_state(workplace)
            endpoint = str(initial_service["endpoint"]).rstrip("/")
            code, _body = http_json("POST", endpoint + "/event", payload={})
            if code != 401:
                raise AssertionError(f"unauthorized IPC returned {code}, expected 401")
            code, _body = declared_oversized_request(endpoint, token(workplace))
            if code != 400:
                raise AssertionError(f"oversized IPC body returned {code}, expected 400")

            pf("runtime", "session-register", "--workplace", str(workplace), "--session", "sess-a", "--agent", "codex-a", "--project-root", str(project_a), "--json")
            pf("runtime", "session-register", "--workplace", str(workplace), "--session", "sess-b", "--agent", "codex-b", "--project-root", str(project_b), "--json")
            registrations = [
                {"session_id": f"parallel-{index}", "agent_id": f"parallel-agent-{index}", "project_root": str(project_a if index % 2 == 0 else project_b)}
                for index in range(12)
            ]
            with ThreadPoolExecutor(max_workers=6) as executor:
                results = list(executor.map(lambda payload: http_json("POST", endpoint + "/session/register", bearer=token(workplace), payload=payload), registrations))
            if any(code != 200 for code, _body in results):
                raise AssertionError(f"concurrent session registration failed: {results}")
            parallel_a = json.loads(pf("runtime", "project-state", "--workplace", str(workplace), "--session", "parallel-0", "--json").stdout)
            parallel_b = json.loads(pf("runtime", "project-state", "--workplace", str(workplace), "--session", "parallel-1", "--json").stdout)
            if parallel_a["project"]["project_id"] == parallel_b["project"]["project_id"]:
                raise AssertionError("concurrent session registration mixed project bindings")

            event_a = write_event(
                root / "event-a.json",
                {
                    "schema_version": 1,
                    "event_id": "long-lived-a-start",
                    "event_type": "agent.session.started",
                    "source": {"adapter": "codex-hooks", "agent": "codex-a", "session_id": "sess-a", "role": "worker"},
                    "project_root": str(project_a),
                    "role": "worker",
                    "payload": {"status": "started"},
                },
            )
            duplicate = json.loads(pf("runtime", "event", "--workplace", str(workplace), "--input", str(event_a), "--json").stdout)
            duplicate = json.loads(pf("runtime", "event", "--workplace", str(workplace), "--input", str(event_a), "--json").stdout)
            if duplicate.get("duplicate") is not True:
                raise AssertionError("duplicate event was not recognized through long-lived runtime")

            state_a = json.loads(pf("runtime", "project-state", "--workplace", str(workplace), "--session", "sess-a", "--json").stdout)
            state_b = json.loads(pf("runtime", "project-state", "--workplace", str(workplace), "--session", "sess-b", "--json").stdout)
            if state_a["project"]["project_id"] == state_b["project"]["project_id"]:
                raise AssertionError("runtime sessions were not isolated by project")
            code, body = http_json(
                "POST",
                endpoint + "/project-state",
                bearer=token(workplace),
                payload={"session_id": "sess-a", "project_root": str(project_b)},
            )
            if code != 403:
                raise AssertionError(f"cross-project session read returned {code}, expected 403: {body}")
            code, body = http_json(
                "POST",
                endpoint + "/event",
                bearer=token(workplace),
                payload={
                    "event_id": "cross-project-event",
                    "event_type": "agent.tool.completed",
                    "source": {"adapter": "generic", "agent": "codex-a", "session_id": "sess-a"},
                    "project_root": str(project_b),
                },
            )
            if code != 403:
                raise AssertionError(f"cross-project session event returned {code}, expected 403: {body}")

            active_worker = project_a / ".pf" / "runtime" / "agent-runs" / "run-a" / "worker-a" / "status.json"
            active_worker.parent.mkdir(parents=True, exist_ok=True)
            active_worker.write_text(json.dumps({"status": "running"}, indent=2) + "\n", encoding="utf-8")
            if int(assert_runtime_ready(workplace).get("active_workers") or 0) < 1:
                raise AssertionError("runtime status did not report active worker state")

            tick = json.loads(pf("runtime", "tick", "--workplace", str(workplace), "--project-root", str(project_a), "--project-root", str(project_b), "--director", "--inspector", "--json").stdout)
            director_results = {item.get("director") for item in tick.get("projects", []) if isinstance(item, dict)}
            if "tick" not in director_results or "skipped_simple" not in director_results:
                raise AssertionError(f"runtime scheduler did not distinguish organized/simple projects: {tick}")

            old_state = service_state(workplace)
            old_state["processforge_core_version"] = "0.0.0-mismatch"
            (runtime_dir(workplace) / "service.json").write_text(json.dumps(old_state, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
            pf("runtime", "doctor", "--workplace", str(workplace), expect=1)

            stop_runtime(workplace)
            runtime_started = False
            stopped = json.loads(pf("runtime", "status", "--workplace", str(workplace), "--json").stdout)
            if stopped.get("status") != "stopped":
                raise AssertionError(f"graceful stop did not persist stopped state: {stopped}")

            stale_root = runtime_dir(workplace)
            stale_root.mkdir(parents=True, exist_ok=True)
            starting = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(30)"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            try:
                starting_instance = "smoke-starting-instance"
                (stale_root / "service.json").write_text(json.dumps({"schema_version": 1, "instance_id": starting_instance, "status": "starting", "health": "starting", "pid": starting.pid, "endpoint": ""}, indent=2) + "\n", encoding="utf-8")
                (stale_root / "runtime.lock").write_text(json.dumps({"instance_id": starting_instance, "pid": starting.pid}) + "\n", encoding="utf-8")
                blocked_start = pf("runtime", "start", "--workplace", str(workplace), "--timeout", "1", expect=1)
                if "still starting" not in (blocked_start.stdout + blocked_start.stderr):
                    raise AssertionError(f"parallel start did not preserve a live starting singleton: {diagnostic_text(blocked_start)}")
                if not (stale_root / "runtime.lock").is_file() or starting.poll() is not None:
                    raise AssertionError("parallel start removed a live starting singleton lock")
                stop_starting = pf("runtime", "stop", "--workplace", str(workplace), "--timeout", "1")
                if "RUNTIME: stopped" not in stop_starting.stdout:
                    raise AssertionError(f"runtime stop did not handle endpoint-unpublished process: {stop_starting.stdout}")
                starting.wait(timeout=5)
            finally:
                if starting.poll() is None:
                    starting.terminate()
                    try:
                        starting.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        starting.kill()

            (stale_root / "service.json").write_text(json.dumps({"schema_version": 1, "status": "ready", "health": "ready", "pid": 999999, "endpoint": "http://127.0.0.1:9"}, indent=2) + "\n", encoding="utf-8")
            (stale_root / "runtime.lock").write_text(json.dumps({"pid": 999999}) + "\n", encoding="utf-8")
            recovered = start_runtime(workplace)
            runtime_started = True
            if recovered.get("status") != "started":
                raise AssertionError(f"runtime did not recover stale singleton state: {recovered}")

            stop_runtime(workplace)
            runtime_started = False
            pid_reused = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(30)"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            try:
                (stale_root / "service.json").write_text(json.dumps({"schema_version": 1, "status": "ready", "health": "ready", "pid": pid_reused.pid, "endpoint": "http://127.0.0.1:9"}, indent=2) + "\n", encoding="utf-8")
                (stale_root / "runtime.lock").write_text(json.dumps({"pid": pid_reused.pid}) + "\n", encoding="utf-8")
                recovered = start_runtime(workplace)
                runtime_started = True
                if recovered.get("status") != "started":
                    raise AssertionError(f"runtime did not recover PID-reuse-like stale state: {recovered}")
            finally:
                pid_reused.terminate()
                try:
                    pid_reused.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    pid_reused.kill()

            pid = int(service_state(workplace)["pid"])
            kill_pid(pid)
            runtime_started = False
            restarted = start_runtime(workplace)
            runtime_started = True
            if restarted.get("status") not in {"started", "already_running"}:
                raise AssertionError(f"runtime did not restart after crash: {restarted}")
            if int(assert_runtime_ready(workplace).get("active_workers") or 0) < 1:
                raise AssertionError("active worker state was lost across runtime crash/restart")

            stop_runtime(workplace)
            runtime_started = False
            pf("runtime-host", "event", "--workplace", str(workplace), "--input", str(event_a), "--json")
            pf("project-mode", "status", "--project-root", str(project_a), "--workplace", str(workplace))
            pf("agent-director-tick", "--workplace", str(workplace), "--project-root", str(project_a))
            pf("execution-inspector-tick", "--project-root", str(project_a))

            manifest_b = project_b / ".pf" / "process-forge.yaml"
            broken_b = project_b / ".pf" / "process-forge.yaml.broken"
            manifest_b.rename(broken_b)
            try:
                state_a_after_b_break = json.loads(pf("runtime-host", "project-state", "--workplace", str(workplace), "--session", "sess-a", "--json").stdout)
                if state_a_after_b_break["project"]["project_id"] != state_a["project"]["project_id"]:
                    raise AssertionError("broken project B affected project A routing")
            finally:
                broken_b.rename(manifest_b)

            pf("events-validate", "--project-root", str(project_a))
            pf("events-validate", "--project-root", str(project_b))
        finally:
            if runtime_started:
                stop_runtime(workplace)

    print("PASS: long-lived runtime smoke")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
