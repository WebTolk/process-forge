"""Long-lived local ProcessForge Runtime process.

This module owns process lifecycle and loopback IPC only. It delegates project
routing, event ingestion, Ledger, Director, Inspector, and projections to
existing PF Core/Runtime Host helpers.
"""

from __future__ import annotations

import argparse
import contextlib
import hmac
import json
import os
import secrets
import signal
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

from . import RUNTIME_PROTOCOL_VERSION
from . import host


RUNTIME_VERSION = "1.0.0-poc"
MAX_BODY_BYTES = 1024 * 1024


def runtime_root(workplace_root: Path) -> Path:
    return workplace_root / "runtime" / "pf-runtime"


def service_path(workplace_root: Path) -> Path:
    return runtime_root(workplace_root) / "service.json"


def token_path(workplace_root: Path) -> Path:
    return runtime_root(workplace_root) / "token.json"


def lock_path(workplace_root: Path) -> Path:
    return runtime_root(workplace_root) / "runtime.lock"


def operator_log_path(workplace_root: Path) -> Path:
    return runtime_root(workplace_root) / "logs" / "operator.log"


def last_json_object(path: Path, *, chunk_size: int = 8192) -> dict[str, Any] | None:
    """Read the newest valid JSON object without scanning an entire journal."""
    try:
        with path.open("rb") as handle:
            handle.seek(0, os.SEEK_END)
            position = handle.tell()
            pending = b""
            while position > 0:
                size = min(chunk_size, position)
                position -= size
                handle.seek(position)
                pending = handle.read(size) + pending
                parts = pending.split(b"\n")
                candidates = parts if position == 0 else parts[1:]
                for raw in reversed(candidates):
                    if not raw.strip():
                        continue
                    try:
                        item = json.loads(raw.decode("utf-8"))
                    except (UnicodeDecodeError, json.JSONDecodeError):
                        continue
                    if isinstance(item, dict):
                        return item
                pending = parts[0] if position > 0 else b""
    except OSError:
        return None
    return None


def read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def write_json_atomic(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{os.getpid()}.{uuid.uuid4().hex}.tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def append_operator_log(workplace_root: Path, core: Any, event: str, **payload: Any) -> None:
    path = operator_log_path(workplace_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    record = {"time": core.now_utc(), "event": event}
    record.update(payload)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")


def load_token(workplace_root: Path) -> str:
    payload = read_json(token_path(workplace_root))
    token = str(payload.get("token") or "")
    if token:
        return token
    token = secrets.token_urlsafe(32)
    write_json_atomic(token_path(workplace_root), {"schema_version": 1, "token": token})
    return token


def token_hash(token: str) -> str:
    import hashlib

    return "sha256:" + hashlib.sha256(token.encode("utf-8")).hexdigest()


def base_state(workplace_root: Path, core: Any, *, status: str, endpoint: str = "", pid: int | None = None, instance_id: str = "") -> dict[str, Any]:
    return {
        "schema_version": 1,
        "runtime_version": RUNTIME_VERSION,
        "protocol_version": RUNTIME_PROTOCOL_VERSION,
        "processforge_core_version": getattr(core, "PROCESSFORGE_VERSION", ""),
        "pid": pid if pid is not None else os.getpid(),
        "instance_id": instance_id,
        "started_at": core.now_utc(),
        "updated_at": core.now_utc(),
        "endpoint": endpoint,
        "workplace_root": str(workplace_root),
        "workplace_id": workplace_root.name,
        "status": status,
        "health": status,
        "token_ref": str(token_path(workplace_root)),
        "scheduler": {
            "jobs": {
                "ledger": {"period_seconds": 5, "last_result": "not_started"},
                "director": {"period_seconds": 10, "last_result": "not_started"},
                "inspector": {"period_seconds": 5, "last_result": "not_started"},
                "projection": {"period_seconds": 30, "last_result": "not_started"},
            }
        },
    }


def save_service_state(workplace_root: Path, core: Any, state: dict[str, Any]) -> None:
    state["updated_at"] = core.now_utc()
    write_json_atomic(service_path(workplace_root), state)


def http_json(method: str, url: str, token: str | None = None, payload: dict[str, Any] | None = None, timeout: float = 5.0) -> tuple[int, dict[str, Any]]:
    data = None if payload is None else json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(url, data=data, method=method)
    request.add_header("Accept", "application/json")
    if data is not None:
        request.add_header("Content-Type", "application/json")
    if token:
        request.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            text = response.read().decode("utf-8")
            return response.status, json.loads(text) if text.strip() else {}
    except urllib.error.HTTPError as exc:
        text = exc.read().decode("utf-8", errors="replace")
        try:
            body = json.loads(text) if text.strip() else {}
        except json.JSONDecodeError:
            body = {"error": text}
        return exc.code, body
    except (urllib.error.URLError, OSError) as exc:
        return 0, {"error": str(exc)}


def inspect_lifecycle(workplace_root: Path, core: Any) -> dict[str, Any]:
    """Return the sole lifecycle interpretation for lock, state, PID and readiness."""
    state = read_json(service_path(workplace_root))
    lock = read_json(lock_path(workplace_root))
    lock_exists = lock_path(workplace_root).exists()
    pid = lock.get("pid")
    instance_id = str(lock.get("instance_id") or "")
    state_instance_id = str(state.get("instance_id") or "")
    matching = bool(instance_id and instance_id == state_instance_id and pid == state.get("pid"))
    pid_running = isinstance(pid, int) and core.process_pid_running(pid)
    state_pid = state.get("pid")
    state_pid_running = isinstance(state_pid, int) and core.process_pid_running(state_pid)
    status = str(state.get("status") or "")
    endpoint = str(state.get("endpoint") or "")
    ready = False
    if matching and pid_running and endpoint:
        code, body = http_json("GET", endpoint.rstrip("/") + "/readyz", timeout=1.0)
        ready = code == 200 and bool(body.get("ready"))
    if matching and pid_running:
        kind = "ready" if ready else (status if status in {"starting", "stopping", "failed"} else "failed")
    elif state_instance_id and state_pid_running:
        # The daemon may have lost its lock file while its service record and
        # endpoint remain live.  This is not stale: starting another daemon
        # would create two owners for one workplace.
        kind = "orphaned"
    elif pid_running:
        # A lock owner whose service record is missing or mismatched is still
        # live.  Never replace it based on an unrelated or absent state file.
        kind = "orphaned"
    elif lock_exists and not isinstance(pid, int):
        # An unreadable/partial lock cannot be proven stale.  Conservative
        # recovery preserves singleton safety until an operator removes it.
        kind = "orphaned"
    elif not lock_exists and status == "stopped":
        kind = "stopped"
    elif not lock_exists and not state:
        kind = "not_running"
    else:
        kind = "stale"
    return {"kind": kind, "state": state, "lock": lock, "pid": pid, "instance_id": instance_id, "matching": matching, "pid_running": pid_running}


def active_service(workplace_root: Path, core: Any) -> tuple[bool, dict[str, Any]]:
    inspection = inspect_lifecycle(workplace_root, core)
    return inspection["kind"] == "ready", inspection["state"]


def wait_for_ready_service(workplace_root: Path, core: Any, timeout: float) -> tuple[bool, dict[str, Any]]:
    deadline = time.monotonic() + max(0.0, timeout)
    while True:
        inspection = inspect_lifecycle(workplace_root, core)
        if inspection["kind"] == "ready":
            return True, inspection["state"]
        if inspection["kind"] != "starting" or time.monotonic() >= deadline:
            return False, inspection["state"]
        time.sleep(0.05)


def cleanup_stale_runtime(workplace_root: Path, core: Any) -> None:
    with singleton_critical_section(workplace_root, core):
        inspection = inspect_lifecycle(workplace_root, core)
        if inspection["kind"] in {"ready", "starting", "stopping", "failed", "orphaned", "stopped", "not_running"}:
            return
        lock_path(workplace_root).unlink(missing_ok=True)
        state = inspection["state"]
        if state:
            state["status"] = "stale"
            state["health"] = "stale"
            state["stale_detected_at"] = core.now_utc()
            write_json_atomic(service_path(workplace_root), state)


def terminate_owned_process(pid: int, core: Any, timeout: float) -> bool:
    try:
        if os.name == "nt":
            subprocess.run(["taskkill", "/PID", str(pid), "/T", "/F"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
        else:
            os.kill(pid, signal.SIGTERM)
    except OSError:
        pass
    deadline = time.monotonic() + max(0.0, timeout)
    while core.process_pid_running(pid) and time.monotonic() < deadline:
        time.sleep(0.05)
    return not core.process_pid_running(pid)


@contextlib.contextmanager
def singleton_critical_section(workplace_root: Path, core: Any | None = None) -> Any:
    """Serialize Runtime lock inspect/reap/create/release per workplace."""
    registry_lock = getattr(core, "registry_file_lock", None)
    if callable(registry_lock):
        with registry_lock(lock_path(workplace_root), timeout_seconds=10.0, stale_after_seconds=10.0):
            yield
        return

    # Runtime unit tests may provide a small core stub.  Keep the fallback
    # cross-process and use a persistent inode so reapers cannot race unlink.
    path = lock_path(workplace_root)
    guard_path = path.with_name(f".{path.name}.lock.guard")
    guard_path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(str(guard_path), os.O_CREAT | os.O_RDWR)
    try:
        if os.name == "nt":
            import msvcrt

            os.lseek(fd, 0, os.SEEK_SET)
            deadline = time.monotonic() + 10.0
            while True:
                try:
                    msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)
                    break
                except OSError:
                    if time.monotonic() >= deadline:
                        raise SystemExit("FAIL: Runtime singleton guard is locked")
                    time.sleep(0.05)
            try:
                yield
            finally:
                os.lseek(fd, 0, os.SEEK_SET)
                msvcrt.locking(fd, msvcrt.LK_UNLCK, 1)
        else:
            import fcntl

            fcntl.flock(fd, fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(fd, fcntl.LOCK_UN)
    finally:
        os.close(fd)


def acquire_singleton(workplace_root: Path, core: Any, instance_id: str) -> int:
    runtime_root(workplace_root).mkdir(parents=True, exist_ok=True)
    path = lock_path(workplace_root)
    with singleton_critical_section(workplace_root, core):
        inspection = inspect_lifecycle(workplace_root, core)
        if inspection["kind"] in {"ready", "starting", "stopping", "failed", "orphaned"}:
            raise SystemExit(f"FAIL: PF Runtime already owns workplace: state={inspection['kind']} pid={inspection['pid']}")
        if inspection["kind"] == "stale":
            path.unlink(missing_ok=True)
        try:
            fd = os.open(str(path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError:
            # The guard makes this unlikely, but re-check under the same
            # critical section before any stale cleanup.  Never unlink an
            # owner that appeared after the first inspection.
            inspection = inspect_lifecycle(workplace_root, core)
            if inspection["kind"] in {"ready", "starting", "stopping", "failed", "orphaned"}:
                raise SystemExit(f"FAIL: PF Runtime already owns workplace: state={inspection['kind']} pid={inspection['pid']}")
            if inspection["kind"] != "stale":
                raise SystemExit("FAIL: PF Runtime singleton lock requires recovery")
            path.unlink(missing_ok=True)
            fd = os.open(str(path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(json.dumps({"instance_id": instance_id, "pid": os.getpid(), "created_at": core.now_utc()}, sort_keys=True) + "\n")
    return os.getpid()


def release_singleton(workplace_root: Path, instance_id: str, core: Any | None = None) -> None:
    with singleton_critical_section(workplace_root, core):
        if str(read_json(lock_path(workplace_root)).get("instance_id") or "") == instance_id:
            lock_path(workplace_root).unlink(missing_ok=True)


class RuntimeProcess:
    def __init__(self, workplace_root: Path, core: Any, *, interval: float) -> None:
        self.workplace_root = workplace_root
        self.core = core
        self.interval = max(0.25, float(interval))
        self.token = load_token(workplace_root)
        self.stop_event = threading.Event()
        self.httpd: ThreadingHTTPServer | None = None
        self.scheduler_thread: threading.Thread | None = None
        self.instance_id = uuid.uuid4().hex
        self.state: dict[str, Any] = base_state(workplace_root, core, status="starting", instance_id=self.instance_id)
        self.state_lock = threading.RLock()
        self._project_errors: dict[str, str] = {}

    def save(self) -> None:
        with self.state_lock:
            save_service_state(self.workplace_root, self.core, self.state)

    def known_project_roots(self) -> list[Path]:
        errors: dict[str, str] = {}
        try:
            state = host.load_state(self.workplace_root)
        except Exception as exc:  # noqa: BLE001 - malformed cache is recoverable.
            self._project_errors = {"host_cache": str(exc)}
            with self.state_lock:
                self.state["project_errors"] = dict(self._project_errors)
                self.state["health"] = "degraded"
            return []
        projects = state.get("projects", [])
        if not isinstance(projects, list):
            errors["host_cache"] = "project cache field is not a list"
            projects = []
        roots: list[Path] = []
        for item in projects:
            if isinstance(item, dict) and item.get("project_root"):
                project_ref = str(item["project_root"])
                try:
                    roots.append(host.resolve_project(project_ref, self.core))
                except SystemExit as exc:
                    errors[project_ref] = str(exc) or "project routing rejected the cached project"
                except Exception as exc:  # noqa: BLE001 - isolate one bad project.
                    errors[project_ref] = str(exc)
            elif item:
                errors["host_cache"] = "project cache contains a malformed entry"
        self._project_errors = errors
        with self.state_lock:
            if errors:
                self.state["project_errors"] = dict(errors)
                self.state["health"] = "degraded"
            else:
                self.state.pop("project_errors", None)
        return roots

    def status_payload(self) -> dict[str, Any]:
        roots = self.known_project_roots()
        try:
            runtime_host = host.load_state(self.workplace_root)
        except Exception as exc:  # noqa: BLE001 - report malformed cache truthfully.
            runtime_host = {}
            self._project_errors["host_cache"] = str(exc)
            with self.state_lock:
                self.state["project_errors"] = dict(self._project_errors)
                self.state["health"] = "degraded"
        with self.state_lock:
            payload = dict(self.state)
        has_errors = bool(payload.get("project_errors") or payload.get("last_scheduler_error"))
        payload["health"] = "degraded" if has_errors else payload.get("health", payload.get("status"))
        scheduler_thread = getattr(self, "scheduler_thread", None)
        payload["scheduler_alive"] = scheduler_thread.is_alive() if scheduler_thread is not None else False
        if scheduler_thread is not None and not scheduler_thread.is_alive() and payload.get("status") == "ready":
            payload["health"] = "degraded"
            payload["last_scheduler_error"] = "scheduler thread is not running"
        payload["known_projects"] = runtime_host.get("projects", [])
        payload["active_agent_sessions"] = len(self.core.iter_agent_presence(self.workplace_root))
        payload["active_workers"] = self.active_worker_count(roots)
        payload["pending_runtime_jobs"] = 0
        payload["last_event"] = self.last_event(roots)
        with self.state_lock:
            current_errors = dict(self._project_errors)
            current_scheduler_error = self.state.get("last_scheduler_error")
        if current_errors:
            payload["project_errors"] = current_errors
            payload["health"] = "degraded"
        if current_scheduler_error:
            payload["last_scheduler_error"] = current_scheduler_error
        return payload

    def active_worker_count(self, roots: list[Path]) -> int:
        count = 0
        for project_root in roots:
            try:
                agent_runs = self.core.locate_flow_root(project_root) / "runtime" / "agent-runs"
                for status_path in agent_runs.glob("*/*/status.json") if agent_runs.is_dir() else []:
                    state = self.core.json_read(status_path)
                    if str(state.get("status") or "") == "running":
                        count += 1
            except Exception as exc:  # noqa: BLE001 - status must survive one project.
                self._project_errors[str(project_root)] = str(exc)
        return count

    def last_event(self, roots: list[Path]) -> dict[str, Any] | None:
        latest: dict[str, Any] | None = None
        for project_root in roots:
            try:
                events_path, _outbox = self.core.event_runtime_paths(project_root)
                if not events_path.is_file():
                    continue
                item = last_json_object(events_path)
                if item is not None:
                    latest = {"project_id": self.core.project_id(project_root), "event_id": item.get("event_id"), "event_type": item.get("event_type"), "time": item.get("time")}
            except Exception as exc:  # noqa: BLE001 - status must survive one project.
                self._project_errors[str(project_root)] = str(exc)
        return latest

    def assert_session_project_scope(self, payload: dict[str, Any]) -> None:
        session_id = str(payload.get("session_id") or "")
        project_ref = payload.get("project_root")
        if not session_id or not project_ref:
            return
        session_project = host.project_for_session(argparse.Namespace(session=session_id, project_root=None), self.workplace_root, self.core)
        requested_project = host.resolve_project(str(project_ref), self.core)
        if self.core.project_id(session_project) != self.core.project_id(requested_project):
            raise PermissionError("session is not authorized for requested project_root")

    def scheduler_loop(self) -> None:
        self.scheduler_thread = threading.current_thread()
        while not self.stop_event.wait(self.interval):
            try:
                roots = self.known_project_roots()
                project_errors = dict(self._project_errors)
                self.core.update_stale_agent_presence(self.workplace_root)
                projects: list[dict[str, Any]] = []
                status = 0
                for project_root in roots:
                    try:
                        item_payload, item_status = host.tick_payload(self.workplace_root, [project_root], self.core, director=True, inspector=True)
                        projects.extend(item_payload.get("projects", []))
                        status = status or item_status
                        if item_status:
                            project_errors[str(project_root)] = f"project scheduler pass failed with status {item_status}"
                    except SystemExit as exc:
                        project_errors[str(project_root)] = str(exc) or "project scheduler pass rejected the project"
                        status = 1
                    except Exception as exc:  # noqa: BLE001 - isolate one bad project.
                        project_errors[str(project_root)] = str(exc)
                        status = 1
                payload = {"status": "ok" if status == 0 and not project_errors else "failed", "projects": projects}
                with self.state_lock:
                    self._project_errors = project_errors
                    jobs = self.state.setdefault("scheduler", {}).setdefault("jobs", {})
                    now = self.core.now_utc()
                    jobs.setdefault("ledger", {})["last_run"] = now
                    jobs["ledger"]["last_result"] = "ok"
                    jobs.setdefault("director", {})["last_run"] = now
                    jobs["director"]["last_result"] = "ok" if status == 0 else "failed"
                    jobs.setdefault("inspector", {})["last_run"] = now
                    jobs["inspector"]["last_result"] = "ok" if status == 0 else "failed"
                    jobs.setdefault("projection", {})["last_run"] = now
                    jobs["projection"]["last_result"] = "ok" if status == 0 else "failed"
                    self.state["last_scheduler_result"] = payload
                    if self._project_errors:
                        self.state["health"] = "degraded"
                        self.state["project_errors"] = dict(self._project_errors)
                        self.state["last_scheduler_error"] = "; ".join(f"{key}: {value}" for key, value in self._project_errors.items())
                    else:
                        self.state.pop("last_scheduler_error", None)
                        self.state.pop("project_errors", None)
                        self.state["health"] = "ready" if self.state.get("status") == "ready" else self.state.get("health", self.state.get("status"))
            except (Exception, SystemExit) as exc:  # noqa: BLE001 - runtime must degrade, not crash on one bad project.
                with self.state_lock:
                    self.state["health"] = "degraded"
                    self.state["last_scheduler_error"] = str(exc)
                try:
                    append_operator_log(self.workplace_root, self.core, "scheduler.error", error=str(exc))
                except OSError:
                    pass  # Preserve the in-memory fault when storage is unavailable.
            try:
                self.save()
            except (Exception, SystemExit) as exc:  # noqa: BLE001 - retry persistence on the next pass.
                with self.state_lock:
                    self.state["health"] = "degraded"
                    self.state["last_scheduler_error"] = str(exc)

    def make_handler(self) -> type[BaseHTTPRequestHandler]:
        runtime = self

        class Handler(BaseHTTPRequestHandler):
            server_version = "ProcessForgeRuntime/1.0"

            def log_message(self, fmt: str, *args: Any) -> None:
                append_operator_log(runtime.workplace_root, runtime.core, "http.request", message=fmt % args)

            def send_json(self, status: int, payload: dict[str, Any]) -> None:
                body = json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
                self.send_response(status)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def authorize(self) -> bool:
                header = self.headers.get("Authorization", "")
                if hmac.compare_digest(header, f"Bearer {runtime.token}"):
                    return True
                append_operator_log(runtime.workplace_root, runtime.core, "auth.failed", path=self.path)
                self.send_json(401, {"error": "unauthorized"})
                return False

            def read_body(self) -> dict[str, Any]:
                length = int(self.headers.get("Content-Length", "0") or "0")
                if length > MAX_BODY_BYTES:
                    raise ValueError("request body too large")
                raw = self.rfile.read(length) if length else b"{}"
                payload = json.loads(raw.decode("utf-8"))
                if not isinstance(payload, dict):
                    raise ValueError("request JSON must be an object")
                return payload

            def do_GET(self) -> None:
                if self.path == "/readyz":
                    self.send_json(200, {"status": runtime.state.get("status"), "ready": runtime.state.get("status") == "ready"})
                    return
                if self.path == "/status":
                    if not self.authorize():
                        return
                    self.send_json(200, runtime.status_payload())
                    return
                self.send_json(404, {"error": "not_found"})

            def do_POST(self) -> None:
                if not self.authorize():
                    return
                try:
                    payload = self.read_body()
                    if self.path == "/event":
                        result = host.ingest_event(payload, runtime.workplace_root, runtime.core)
                        self.send_json(200, result)
                    elif self.path == "/session/register":
                        project_ref = payload.get("project_root") or payload.get("cwd")
                        session = str(payload.get("session_id") or "")
                        agent = str(payload.get("agent_id") or payload.get("agent") or "")
                        if not project_ref or not session:
                            self.send_json(400, {"error": "project_root/cwd and session_id are required"})
                            return
                        handle = host.route_project(str(project_ref), runtime.workplace_root, runtime.core)
                        registration = {"event_type": "agent.session.started", "project_root": str(project_ref), "session_id": session, "agent_id": agent, "source": {"adapter": "runtime-session-register", "session_id": session, "agent": agent}}
                        host.ingest_event(registration, runtime.workplace_root, runtime.core)
                        with host.state_lock():
                            state = host.load_state(runtime.workplace_root)
                            host.remember_project(state, handle)
                            host.remember_session(state, session, handle, agent, runtime.core)
                            host.save_state(runtime.workplace_root, state, runtime.core)
                        self.send_json(200, {"session_id": session, "project": handle})
                    elif self.path == "/project-state":
                        runtime.assert_session_project_scope(payload)
                        self.send_json(200, host.project_state_payload(runtime.workplace_root, runtime.core, session=str(payload.get("session_id") or ""), project_root_ref=payload.get("project_root")))
                    elif self.path == "/work-state":
                        runtime.assert_session_project_scope(payload)
                        self.send_json(200, host.work_state_payload(runtime.workplace_root, runtime.core, session=str(payload.get("session_id") or ""), project_root_ref=payload.get("project_root")))
                    elif self.path == "/resolve":
                        runtime.assert_session_project_scope(payload)
                        self.send_json(200, host.resolve_payload(runtime.workplace_root, runtime.core, session=str(payload.get("session_id") or ""), project_root_ref=payload.get("project_root"), resource_id=str(payload.get("resource_id") or "") or None))
                    elif self.path == "/tick":
                        roots = [host.resolve_project(str(item), runtime.core) for item in payload.get("project_roots", []) if item]
                        result, status = host.tick_payload(runtime.workplace_root, roots, runtime.core, director=bool(payload.get("director")), inspector=bool(payload.get("inspector")))
                        self.send_json(200 if status == 0 else 500, result)
                    elif self.path == "/shutdown":
                        if not self.authorize():
                            return
                        with runtime.state_lock:
                            runtime.state["status"] = "stopping"
                            runtime.state["health"] = "stopping"
                        runtime.save()
                        self.send_json(200, {"status": "stopping"})
                        runtime.stop_event.set()
                        if runtime.httpd:
                            threading.Thread(target=runtime.httpd.shutdown, daemon=True).start()
                    else:
                        self.send_json(404, {"error": "not_found"})
                except Exception as exc:  # noqa: BLE001 - return structured local IPC errors.
                    if isinstance(exc, PermissionError):
                        append_operator_log(runtime.workplace_root, runtime.core, "request.forbidden", path=self.path, error=str(exc))
                        self.send_json(403, {"error": str(exc)})
                        return
                    append_operator_log(runtime.workplace_root, runtime.core, "request.error", path=self.path, error=str(exc))
                    self.send_json(400, {"error": str(exc)})

        return Handler

    def serve(self, port: int) -> int:
        acquire_singleton(self.workplace_root, self.core, self.instance_id)
        try:
            self.state = base_state(self.workplace_root, self.core, status="starting", instance_id=self.instance_id)
            self.state["token_hash"] = token_hash(self.token)
            self.save()
            self.httpd = ThreadingHTTPServer(("127.0.0.1", int(port)), self.make_handler())
            host_name, bound_port = self.httpd.server_address
            endpoint = f"http://{host_name}:{bound_port}"
            self.state["endpoint"] = endpoint
            self.state["status"] = "ready"
            self.state["health"] = "ready"
            self.save()
            append_operator_log(self.workplace_root, self.core, "runtime.started", endpoint=endpoint, pid=os.getpid())
            self.scheduler_thread = threading.Thread(target=self.scheduler_loop, daemon=True)
            self.scheduler_thread.start()
            self.httpd.serve_forever(poll_interval=0.2)
            self.state["status"] = "stopped"
            self.state["health"] = "stopped"
            self.save()
            append_operator_log(self.workplace_root, self.core, "runtime.stopped", pid=os.getpid())
            return 0
        except BaseException as exc:
            with self.state_lock:
                self.state["status"] = "failed"
                self.state["health"] = "failed"
                self.state["last_error"] = str(exc)
            self.save()
            append_operator_log(self.workplace_root, self.core, "runtime.failed", pid=os.getpid(), error=str(exc))
            raise
        finally:
            release_singleton(self.workplace_root, self.instance_id, self.core)


def command_serve(args: argparse.Namespace, core: Any) -> int:
    workplace_root = core.resolve_workplace_root(getattr(args, "workplace", None))
    runtime = RuntimeProcess(workplace_root, core, interval=float(getattr(args, "interval", 2.0) or 2.0))
    return runtime.serve(int(getattr(args, "port", 0) or 0))


def command_start(args: argparse.Namespace, core: Any) -> int:
    workplace_root = core.resolve_workplace_root(getattr(args, "workplace", None))
    inspection = inspect_lifecycle(workplace_root, core)
    state = inspection["state"]
    if inspection["kind"] == "ready":
        payload = {"status": "already_running", "pid": state.get("pid"), "endpoint": state.get("endpoint")}
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) if getattr(args, "json", False) else f"RUNTIME: already running pid={payload['pid']} endpoint={payload['endpoint']}")
        return 0
    if inspection["kind"] == "starting":
        ready, ready_state = wait_for_ready_service(workplace_root, core, float(getattr(args, "timeout", 10.0) or 10.0))
        if not ready:
            raise SystemExit(f"FAIL: PF Runtime is still starting for workplace: pid={inspection['pid']}")
        payload = {"status": "already_running", "pid": ready_state.get("pid"), "endpoint": ready_state.get("endpoint")}
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) if getattr(args, "json", False) else f"RUNTIME: already running pid={payload['pid']} endpoint={payload['endpoint']}")
        return 0
    if inspection["kind"] in {"stopping", "failed", "orphaned"}:
        raise SystemExit(f"FAIL: PF Runtime requires stop/recovery before start: state={inspection['kind']} pid={inspection['pid']}")
    cleanup_stale_runtime(workplace_root, core)
    log_dir = runtime_root(workplace_root) / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    stdout = (log_dir / "runtime.stdout.log").open("ab")
    stderr = (log_dir / "runtime.stderr.log").open("ab")
    command = [sys.executable, str(core.ROOT / "tools" / "processforge.py"), "runtime", "serve", "--workplace", str(workplace_root), "--port", str(int(getattr(args, "port", 0) or 0)), "--interval", str(float(getattr(args, "interval", 2.0) or 2.0))]
    creationflags = 0
    kwargs: dict[str, Any] = {}
    if os.name == "nt":
        creationflags = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0) | getattr(subprocess, "DETACHED_PROCESS", 0)
        kwargs["creationflags"] = creationflags
    else:
        kwargs["start_new_session"] = True
    proc = subprocess.Popen(command, cwd=str(core.ROOT), stdout=stdout, stderr=stderr, stdin=subprocess.DEVNULL, close_fds=True, **kwargs)
    stdout.close()
    stderr.close()
    deadline = time.monotonic() + float(getattr(args, "timeout", 10.0) or 10.0)
    ready_state: dict[str, Any] = {}
    while time.monotonic() < deadline:
        if proc.poll() is not None:
            raise SystemExit(f"FAIL: runtime exited during startup with code {proc.returncode}")
        ready_state = read_json(service_path(workplace_root))
        endpoint = str(ready_state.get("endpoint") or "")
        if endpoint and ready_state.get("status") == "ready":
            code, body = http_json("GET", endpoint.rstrip("/") + "/readyz", timeout=1.0)
            if code == 200 and body.get("ready"):
                payload = {"status": "started", "pid": ready_state.get("pid"), "endpoint": endpoint}
                print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) if getattr(args, "json", False) else f"RUNTIME: started pid={payload['pid']} endpoint={payload['endpoint']}")
                return 0
        time.sleep(0.1)
    proc.terminate()
    try:
        proc.wait(timeout=2)
    except subprocess.TimeoutExpired:
        proc.kill()
    cleanup_stale_runtime(workplace_root, core)
    raise SystemExit("FAIL: runtime did not become ready before timeout")


def command_stop(args: argparse.Namespace, core: Any) -> int:
    workplace_root = core.resolve_workplace_root(getattr(args, "workplace", None))
    inspection = inspect_lifecycle(workplace_root, core)
    state = inspection["state"]
    if inspection["kind"] == "orphaned":
        endpoint = str(state.get("endpoint") or "")
        code, body = http_json("GET", endpoint.rstrip("/") + "/readyz", timeout=1.0) if endpoint else (0, {})
        if code != 200 or not body.get("ready"):
            raise SystemExit(f"FAIL: orphaned PF Runtime has no verified ready endpoint: pid={inspection['pid']}")
        inspection["kind"] = "ready"
    if inspection["kind"] == "starting":
        ready, state = wait_for_ready_service(workplace_root, core, min(2.0, float(getattr(args, "timeout", 10.0) or 10.0)))
        if not ready:
            pid = inspection["pid"]
            if not isinstance(pid, int) or not terminate_owned_process(pid, core, float(getattr(args, "timeout", 10.0) or 10.0)):
                raise SystemExit(f"FAIL: runtime starting process did not stop: pid={pid}")
            cleanup_stale_runtime(workplace_root, core)
            print("RUNTIME: stopped")
            return 0
    elif inspection["kind"] in {"stopping", "failed"}:
        pid = inspection["pid"]
        if not isinstance(pid, int) or not terminate_owned_process(pid, core, float(getattr(args, "timeout", 10.0) or 10.0)):
            raise SystemExit(f"FAIL: runtime process did not stop: pid={pid}")
        cleanup_stale_runtime(workplace_root, core)
        print("RUNTIME: stopped")
        return 0
    elif inspection["kind"] != "ready":
        cleanup_stale_runtime(workplace_root, core)
        print("RUNTIME: not running")
        return 0
    token = load_token(workplace_root)
    endpoint = str(state.get("endpoint") or "")
    code, body = http_json("POST", endpoint.rstrip("/") + "/shutdown", token=token, payload={}, timeout=2.0)
    if code != 200:
        raise SystemExit(f"FAIL: runtime stop request failed: {code} {body}")
    pid = state.get("pid")
    deadline = time.monotonic() + float(getattr(args, "timeout", 10.0) or 10.0)
    while isinstance(pid, int) and core.process_pid_running(pid) and time.monotonic() < deadline:
        time.sleep(0.1)
    if isinstance(pid, int) and core.process_pid_running(pid):
        raise SystemExit(f"FAIL: runtime did not stop before timeout: pid={pid}")
    cleanup_stale_runtime(workplace_root, core)
    print("RUNTIME: stopped")
    return 0


def command_restart(args: argparse.Namespace, core: Any) -> int:
    command_stop(args, core)
    return command_start(args, core)


def add_runtime_truth(payload: dict[str, Any], core: Any, *, running: bool) -> dict[str, Any]:
    runtime_version = str(payload.get("runtime_version") or RUNTIME_VERSION)
    status = str(payload.get("status") or "")
    payload["installed_pf"] = {"version": str(getattr(core, "PROCESSFORGE_VERSION", ""))}
    payload["runtime"] = {"running": bool(running), "status": status, "health": str(payload.get("health") or status)}
    if runtime_version:
        instance_status = "current" if running else ("historical" if status not in {"", "not_running"} else "not_available")
        payload["last_runtime_instance"] = {"version": runtime_version, "status": instance_status}
    else:
        payload["last_runtime_instance"] = {"version": "", "status": "not_available"}
    return payload


def status_payload(workplace_root: Path, core: Any) -> dict[str, Any]:
    active, state = active_service(workplace_root, core)
    if not active and state:
        state = dict(state)
        if state.get("status") == "stopped":
            state["health"] = "stopped"
            return add_runtime_truth(state, core, running=False)
        state["status"] = "stale"
        state["health"] = "stale"
        return add_runtime_truth(state, core, running=False)
    if not active:
        return add_runtime_truth({"schema_version": 1, "status": "not_running", "health": "stopped", "workplace_root": str(workplace_root)}, core, running=False)
    token = load_token(workplace_root)
    endpoint = str(state.get("endpoint") or "")
    code, body = http_json("GET", endpoint.rstrip("/") + "/status", token=token, timeout=2.0)
    if code == 200:
        return add_runtime_truth(body, core, running=True)
    state = dict(state)
    state["health"] = "degraded"
    state["last_status_error"] = body
    return add_runtime_truth(state, core, running=True)


def command_status(args: argparse.Namespace, core: Any) -> int:
    workplace_root = core.resolve_workplace_root(getattr(args, "workplace", None))
    payload = status_payload(workplace_root, core)
    if getattr(args, "json", False):
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(f"RUNTIME: {payload.get('status')} health={payload.get('health')} pid={payload.get('pid', '')} endpoint={payload.get('endpoint', '')}")
        print(f"PROJECTS: {len(payload.get('known_projects', [])) if isinstance(payload.get('known_projects'), list) else 0}")
        print(f"AGENT_SESSIONS: {payload.get('active_agent_sessions', 0)}")
        print(f"ACTIVE_WORKERS: {payload.get('active_workers', 0)}")
    return 0 if payload.get("status") not in {"failed"} else 1


def command_doctor(args: argparse.Namespace, core: Any) -> int:
    workplace_root = core.resolve_workplace_root(getattr(args, "workplace", None))
    active, state = active_service(workplace_root, core)
    checks: list[Any] = []
    checks.append(core.check("PASS" if runtime_root(workplace_root).parent.is_dir() else "FAIL", "workplace runtime root exists"))
    checks.append(core.check("PASS" if token_path(workplace_root).is_file() else "WARN", "runtime auth token exists"))
    checks.append(core.check("PASS" if not active or state.get("protocol_version") == RUNTIME_PROTOCOL_VERSION else "FAIL", "runtime protocol version compatible"))
    checks.append(core.check("PASS" if not active or state.get("processforge_core_version") == getattr(core, "PROCESSFORGE_VERSION", "") else "FAIL", "runtime core version compatible"))
    checks.append(core.check("PASS" if active or not lock_path(workplace_root).exists() else "WARN", "singleton lock is not stale"))
    host_state = host.load_state(workplace_root)
    checks.append(core.check("PASS" if isinstance(host_state.get("projects"), list) else "FAIL", "project handle cache readable"))
    checks.append(core.check("PASS" if core.workplace_agent_ledger_path(workplace_root).parent.is_dir() else "FAIL", "Agent Ledger path accessible"))
    payload = status_payload(workplace_root, core)
    checks.append(core.check("PASS" if payload.get("health") in {"ready", "stopped", "stale"} else "WARN", f"runtime health is {payload.get('health')}"))
    return core.print_checks(checks)


def runtime_request(args: argparse.Namespace, core: Any, path: str, payload: dict[str, Any]) -> int:
    workplace_root = core.resolve_workplace_root(getattr(args, "workplace", None))
    active, state = active_service(workplace_root, core)
    if not active:
        raise SystemExit("FAIL: runtime is not running")
    token = load_token(workplace_root)
    endpoint = str(state.get("endpoint") or "")
    code, body = http_json("POST", endpoint.rstrip("/") + path, token=token, payload=payload, timeout=5.0)
    print(json.dumps(body, ensure_ascii=False, indent=2, sort_keys=True) if getattr(args, "json", False) else core.dump_yaml(body))
    return 0 if 200 <= code < 300 else 1


def command_event(args: argparse.Namespace, core: Any) -> int:
    raw = host.load_input(args)
    if getattr(args, "project_root", None):
        raw["project_root"] = getattr(args, "project_root")
    return runtime_request(args, core, "/event", raw)


def command_session_register(args: argparse.Namespace, core: Any) -> int:
    payload = {"session_id": args.session, "agent_id": args.agent or "", "project_root": args.project_root or "", "cwd": args.cwd or ""}
    return runtime_request(args, core, "/session/register", payload)


def command_project_state(args: argparse.Namespace, core: Any) -> int:
    return runtime_request(args, core, "/project-state", {"session_id": args.session or "", "project_root": args.project_root or ""})


def command_work_state(args: argparse.Namespace, core: Any) -> int:
    return runtime_request(args, core, "/work-state", {"session_id": args.session or "", "project_root": args.project_root or ""})


def command_resolve(args: argparse.Namespace, core: Any) -> int:
    return runtime_request(args, core, "/resolve", {"session_id": args.session or "", "project_root": args.project_root or "", "resource_id": getattr(args, "resource", "") or ""})


def command_tick(args: argparse.Namespace, core: Any) -> int:
    return runtime_request(args, core, "/tick", {"project_roots": getattr(args, "project_root", []), "director": bool(args.director), "inspector": bool(args.inspector)})
