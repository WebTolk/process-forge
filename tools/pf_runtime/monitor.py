"""Read-only, bounded terminal projection of existing local Runtime state."""
from __future__ import annotations

import argparse
import contextlib
from datetime import datetime, timezone
import ipaddress
import json
import math
import os
from pathlib import Path
import re
import select
import shutil
import socket
import sys
import time
import unicodedata
from urllib.parse import urlsplit
from typing import Any, Callable, TextIO

from . import service

STATE_LIMIT = 1024 * 1024
LOCK_LIMIT = 64 * 1024
STALE_SECONDS = 15
PROBE_SECONDS = 0.75
MAX_JOBS = 32


def read_record(path: Path, limit: int = STATE_LIMIT) -> tuple[dict[str, Any], str]:
    try:
        with path.open("rb") as stream:
            raw = stream.read(limit + 1)
        if len(raw) > limit:
            return {}, "oversize"
        data = json.loads(raw.decode("utf-8"))
        return (data, "ok") if isinstance(data, dict) else ({}, "invalid")
    except FileNotFoundError:
        return {}, "missing"
    except (OSError, ValueError, RecursionError):
        return {}, "unreadable"


def positive_pid(value: Any) -> bool:
    return type(value) is int and 0 < value <= 2147483647


def pid_alive(pid: int) -> bool | None:
    """None means the probe failed; never equate uncertainty with a dead owner."""
    try:
        if os.name == "nt":
            import ctypes
            from ctypes import wintypes
            kernel = ctypes.WinDLL("kernel32", use_last_error=True)
            kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
            kernel.OpenProcess.restype = wintypes.HANDLE
            kernel.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
            kernel.WaitForSingleObject.restype = wintypes.DWORD
            kernel.CloseHandle.argtypes = [wintypes.HANDLE]
            kernel.CloseHandle.restype = wintypes.BOOL
            handle = kernel.OpenProcess(0x100000, False, pid)  # SYNCHRONIZE only
            if not handle:
                return False if ctypes.get_last_error() == 87 else None
            try:
                result = kernel.WaitForSingleObject(handle, 0)
                return True if result == 258 else False if result == 0 else None
            finally:
                kernel.CloseHandle(handle)
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except (OSError, AttributeError, TypeError, ValueError):
        return None


def probe_ready(endpoint: str) -> tuple[bool | None, str]:
    """Minimal loopback HTTP probe with an absolute deadline and byte ceilings.

    No token, proxy, redirect, DNS lookup or full /status request is involved.
    Runtime's /readyz uses Content-Length and closes an HTTP/1.0 connection.
    """
    if not isinstance(endpoint, str):
        return None, "endpoint_rejected"
    try:
        url = urlsplit(endpoint)
        address = ipaddress.ip_address(url.hostname or "")
        port = url.port
        if (url.scheme != "http" or not address.is_loopback or not port or
                url.username is not None or url.password is not None or
                url.path not in {"", "/"} or url.query or url.fragment):
            return None, "endpoint_rejected"
    except (ValueError, TypeError):
        return None, "endpoint_rejected"
    deadline = time.monotonic() + PROBE_SECONDS
    try:
        # A numeric address avoids DNS/proxy behavior. The deadline is shared by
        # connect, send and every receive, including slow/trickling responses.
        with socket.create_connection((str(address), port), timeout=PROBE_SECONDS) as conn:
            conn.settimeout(max(0.001, deadline - time.monotonic()))
            host = f"[{address}]" if address.version == 6 else str(address)
            conn.sendall(f"GET /readyz HTTP/1.0\r\nHost: {host}:{port}\r\nConnection: close\r\n\r\n".encode("ascii"))
            raw = b""
            length = None
            header_end = None
            while True:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    return None, "probe_timeout"
                conn.settimeout(remaining)
                chunk = conn.recv(4096)
                if not chunk:
                    return None, "probe_invalid"
                raw += chunk
                if header_end is None and b"\r\n\r\n" in raw:
                    header, _ = raw.split(b"\r\n\r\n", 1)
                    header_end = len(header) + 4
                    lines = header.split(b"\r\n")
                    if header_end > 8192 or not re.fullmatch(rb"HTTP/1\.[01] 200(?: .*)?", lines[0]):
                        return None, "probe_invalid"
                    lengths = [line.split(b":", 1)[1].strip() for line in lines[1:] if line.lower().startswith(b"content-length:")]
                    if len(lengths) != 1 or not lengths[0].isdigit() or any(line.lower().startswith(b"transfer-encoding:") for line in lines[1:]):
                        return None, "probe_invalid"
                    length = int(lengths[0])
                    if length > 4096:
                        return None, "probe_oversize"
                if header_end is None and len(raw) > 8192:
                    return None, "probe_oversize"
                if header_end is not None and len(raw) >= header_end + length:
                    body = json.loads(raw[header_end:header_end + length].decode("utf-8"))
                    if not isinstance(body, dict) or type(body.get("ready")) is not bool:
                        return None, "probe_invalid"
                    return body["ready"], "ready" if body["ready"] else "not_ready"
    except (TimeoutError, socket.timeout):
        return None, "probe_timeout"
    except (OSError, ValueError, RecursionError):
        return None, "probe_failed"


def freshness(value: Any, now: datetime, maximum_age: float = STALE_SECONDS) -> dict[str, Any]:
    try:
        stamp = datetime.fromisoformat(value.replace("Z", "+00:00")) if isinstance(value, str) else None
        if stamp is None or stamp.tzinfo is None:
            raise ValueError
        age = (now - stamp).total_seconds()
        if age < 0 or not math.isfinite(age):
            raise ValueError
        return {"status": "fresh" if age <= maximum_age else "stale", "age_seconds": round(age, 1)}
    except (ValueError, TypeError, OverflowError):
        return {"status": "unknown", "age_seconds": None}


def safe_text(value: Any, limit: int = 64, *, ascii_only: bool = False) -> str:
    text = value if isinstance(value, str) else "unknown"
    text = "".join(c if not unicodedata.category(c).startswith("C") and c not in "\r\n\t" else "?" for c in text[:limit])
    return text.encode("ascii", errors="replace").decode("ascii") if ascii_only else text


def version(value: Any) -> str:
    return value if isinstance(value, str) and re.fullmatch(r"[0-9][0-9A-Za-z.+-]{0,63}", value) else "unknown"


def applied_interval(configuration: Any) -> float | None:
    from processforge_core.configuration import MetricsConfig

    try:
        return MetricsConfig(configuration["metrics_interval_seconds"]).interval_seconds
    except (KeyError, TypeError, ValueError):
        return None


def collect_snapshot(workplace: Path, cli_version: str, *, now: datetime | None = None,
                     alive: Callable = pid_alive, probe: Callable = probe_ready) -> dict[str, Any]:
    now = now or datetime.now(timezone.utc)
    state, state_reason = read_record(service.service_path(workplace))
    lock, lock_reason = read_record(service.lock_path(workplace), LOCK_LIMIT)
    cache, cache_reason = read_record(workplace / "runtime" / "pf-runtime-host" / "state.json")
    issues = []
    for label, reason in [("state", state_reason), ("lock", lock_reason), ("cache", cache_reason)]:
        if reason not in {"ok", "missing"}:
            issues.append(label + "_" + reason)
    pids = {p for p in (state.get("pid"), lock.get("pid")) if positive_pid(p)}
    observed = {pid: alive(pid) for pid in pids}
    lock_alive = observed.get(lock.get("pid"), False) if positive_pid(lock.get("pid")) else False
    state_alive = observed.get(state.get("pid"), False) if positive_pid(state.get("pid")) else False
    matching = bool(isinstance(lock.get("instance_id"), str) and lock["instance_id"] and
                    lock.get("instance_id") == state.get("instance_id") and
                    positive_pid(lock.get("pid")) and lock.get("pid") == state.get("pid"))
    ready, probe_reason = (None, "not_probed")
    if matching and lock_alive:
        ready, probe_reason = probe(state.get("endpoint", ""))
        if ready is None:
            issues.append(probe_reason)
    if None in observed.values():
        issues.append("pid_probe_unknown")
    state_after, after_reason = read_record(service.service_path(workplace))
    lock_after, lock_after_reason = read_record(service.lock_path(workplace), LOCK_LIMIT)
    identity = lambda item: (item.get("pid"), item.get("instance_id"), item.get("endpoint"))
    if identity(state_after) != identity(state) or lock_after != lock or after_reason != state_reason or lock_after_reason != lock_reason:
        issues.append("owner_changed")
    else:
        state = state_after
    uncertain = (state_reason not in {"ok", "missing"} or lock_reason not in {"ok", "missing"} or
                 "owner_changed" in issues or "pid_probe_unknown" in issues or (matching and lock_alive and ready is None))
    if state_reason == "ok" and not state:
        uncertain = True
        issues.append("state_invalid")
    lifecycle = "unknown" if uncertain else service.classify_lifecycle(
        state, lock, lock_exists=lock_reason != "missing", pid_running=bool(lock_alive),
        state_pid_running=bool(state_alive), ready=ready is True)
    interval = applied_interval(state.get("configuration")) if lifecycle == "ready" else None
    age = freshness(state.get("updated_at"), now, max(15, 2 * interval + 5) if interval is not None else STALE_SECONDS)
    health = state.get("health") if lifecycle == "ready" and age["status"] == "fresh" else "unknown"
    if not isinstance(health, str) or health not in {"ready", "degraded", "failed", "starting", "stopping", "stopped"}:
        health = "unknown"
    scheduler = state.get("scheduler")
    jobs = scheduler.get("jobs") if isinstance(scheduler, dict) else None
    rows = []
    if isinstance(jobs, dict):
        for name, job in list(jobs.items())[:MAX_JOBS]:
            job = job if isinstance(job, dict) else {}
            result = job.get("last_result")
            rows.append({"name": safe_text(name, 24), "last_result": result if isinstance(result, str) and result in {"ok", "failed", "not_started"} else "unknown",
                         "freshness": freshness(job.get("last_run"), now)})
        if len(jobs) > MAX_JOBS:
            issues.append("jobs_truncated")
    cache_age = freshness(cache.get("updated_at"), now)
    compact = service.metrics_core().project(state.get("metrics"), state.get("instance_id"), now=now.timestamp()) if lifecycle == "ready" and age["status"] == "fresh" else None
    if "metrics" in state and compact is None:
        issues.append("metrics_unavailable")
    registration = {"projects": len(cache["projects"]) if isinstance(cache.get("projects"), list) else None,
                    "sessions": len(cache["sessions"]) if isinstance(cache.get("sessions"), dict) else None,
                    "freshness": cache_age}
    if compact:
        registration = {**compact["groups"]["registrations"]["counts"],
                        "freshness": {"status": "fresh", "age_seconds": compact["age_seconds"]}}
        issues = [i for i in issues if not i.startswith("cache_")]
    configuration = state.get("configuration")
    config_status = configuration.get("status") if isinstance(configuration, dict) and lifecycle == "ready" else None
    if config_status == "invalid":
        issues.append("configuration_invalid")
    uptime = freshness(state.get("started_at"), now)["age_seconds"] if lifecycle == "ready" else None
    return {"schema_version": 1, "kind": "pf.runtime.monitor", "observed_at": now.isoformat(),
            "source": "bounded_local_state_and_loopback_readyz", "workplace": safe_text(workplace.name),
            "cli_version": version(cli_version), "state_freshness": age,
            "runtime": {"lifecycle": lifecycle, "health": health, "owner_pid": lock.get("pid") if matching and lock_alive and not uncertain else None,
                        "owner_alive": lock_alive if matching and not uncertain else None,
                        "instance_version": version(state.get("runtime_version")), "readiness": probe_reason,
                        "uptime_seconds": uptime},
            "configuration": {"status": config_status if config_status in {"valid", "invalid"} else "unknown", "interval_seconds": interval},
            "scheduler": {"source": "cached_job_results", "jobs": rows},
            "registrations": registration,
            "metrics": compact,
            "activity": {key: None for key in ["sessions", "workers", "work_waiting", "leases", "event_rate", "backlog", "mcp", "hooks"]},
            "issues": issues}


def cell_width(text: str) -> int:
    return sum(0 if unicodedata.combining(c) else 2 if unicodedata.east_asian_width(c) in {"W", "F"} else 1 for c in text)


def crop(text: str, columns: int, *, ascii_only: bool = False) -> str:
    text = safe_text(text, 512, ascii_only=ascii_only)
    result = ""
    width = 0
    for char in text:
        amount = cell_width(char)
        if width + amount > columns:
            break
        if not result and amount == 0:
            continue
        result += char
        width += amount
    return result


def render_details(snapshot: dict[str, Any], columns: int = 80, lines: int = 24, *, ascii_only: bool = False) -> list[str]:
    runtime = snapshot["runtime"]
    age = snapshot["state_freshness"]
    age_text = "unknown" if age["age_seconds"] is None else f"{age['age_seconds']:.1f}s"
    number = lambda value: "unknown" if value is None else str(value)
    rows = [f"Runtime: {runtime['lifecycle'].upper()} | health: {runtime['health']}",
            f"PF {'-' if ascii_only else '·'} ProcessForge Server monitor",
            f"Workplace: {snapshot['workplace']} | owner PID: {number(runtime['owner_pid'])}",
            f"CLI: {snapshot['cli_version']} | instance: {runtime['instance_version']}",
            f"State: {age['status']} | age: {age_text} | probe: {runtime['readiness']}",
            "Scheduler (cached results; no thread-health claim):"]
    for job in snapshot["scheduler"]["jobs"]:
        rows.append(f"  {job['name']}: {job['last_result']} [{job['freshness']['status']}]")
    if not snapshot["scheduler"]["jobs"]:
        rows.append("  unknown")
    reg = snapshot["registrations"]
    rows.extend([f"Registered projects: {number(reg['projects'])} | cached sessions: {number(reg['sessions'])}",
                 f"Registry cache: {reg['freshness']['status']} (registrations are not activity)"])
    compact = snapshot.get("metrics")
    if compact:
        rows.append(f"Activity sample: {compact['age_seconds']:.1f}s; partial counts are lower bounds")
        labels = {"sessions": "Session presence", "workers": "Reported workers", "work": "Work records", "leases": "Leases"}
        for key, label in labels.items():
            item = compact["groups"][key]
            values = ", ".join(f"{k}={v if item['coverage'] == 'complete' else '>=' + str(v)}" for k, v in item["observed"].items())
            rows.append(f"{label}: {values} [{item['coverage']}]")
    else:
        rows.append("Active sessions/workers/Work/leases: unknown")
    rows.append("Waiting for user/events/backlog/MCP/hooks: unknown (no aggregate coverage)")
    if snapshot["issues"]:
        rows.append("Observation: " + ", ".join(snapshot["issues"]))
    footer = "Q / Esc / Ctrl+C: close monitor; server unchanged"
    height = max(1, lines - 1)
    rows = rows[:max(1, height - 1)] + ([footer] if height > 1 else [])
    return [crop(row, max(1, columns - 1), ascii_only=ascii_only) for row in rows]


def banner(ascii_only: bool = False) -> list[str]:
    return (["PP  FF   ProcessForge Server", "P   F    PF"] if ascii_only else
            ["█▀█ █▀▀   ProcessForge Server", "█▀▀ █▀    PF"])


def render(snapshot: dict[str, Any], columns: int = 80, lines: int = 24, *, ascii_only: bool = False,
           details: bool = False, decorative: bool = False) -> list[str]:
    if details:
        return render_details(snapshot, columns, lines, ascii_only=ascii_only)
    runtime = snapshot["runtime"]
    number = lambda value: "unknown" if value is None else str(value)
    rows = [f"Runtime: {runtime['lifecycle'].upper()} | health: {runtime['health']}"]
    rows.extend(banner(ascii_only) if decorative and columns >= 35 and lines >= 16 else ["PF | ProcessForge Server"])
    rows += [f"Workplace: {snapshot['workplace']} | PID: {number(runtime['owner_pid'])}",
             f"CLI: {snapshot['cli_version']} | instance: {runtime['instance_version']}",
             f"Uptime: {number(runtime.get('uptime_seconds'))}s"]
    compact = snapshot.get("metrics")
    interval = snapshot.get("configuration", {}).get("interval_seconds")
    if compact:
        rows.append(f"Metrics: {compact['age_seconds']:.1f}s old | interval: {number(interval)}s")
        labels = {"registrations": "Registered", "sessions": "Session presence", "workers": "Reported workers",
                  "work": "Work records", "leases": "Leases"}
        for key, label in labels.items():
            item = compact["groups"][key]
            values = ", ".join(f"{k}={v if item['coverage'] == 'complete' else '>=' + str(v)}" for k, v in item["observed"].items())
            rows.append(f"{label}: {values}" + (" [partial]" if item["coverage"] != "complete" else ""))
    else:
        rows += [f"Metrics: unavailable | interval: {number(interval)}s",
                 f"Registered projects: {number(snapshot['registrations']['projects'])}",
                 "Sessions / workers / Work / leases: unknown"]
    if snapshot["issues"]:
        rows.append("Observation: " + ", ".join(snapshot["issues"]))
    rows.append("--details: scheduler and observation diagnostics")
    footer = "Q / Esc / Ctrl+C: close monitor; server unchanged"
    height = max(1, lines - 1)
    rows = rows[:max(1, height - 1)] + ([footer] if height > 1 else [])
    return [crop(row, max(1, columns - 1), ascii_only=ascii_only) for row in rows]


class Screen:
    """Small diff renderer; external text never supplies terminal controls."""
    def __init__(self, stream: TextIO) -> None:
        self.stream = stream
        self.rows: list[str] = []
        self.size = None

    def draw(self, rows: list[str], size: tuple[int, int]) -> None:
        output = []
        if self.size != size:
            output.append("\x1b[2J")
            self.rows = []
        for index in range(max(len(rows), len(self.rows))):
            row = rows[index] if index < len(rows) else ""
            if index >= len(self.rows) or row != self.rows[index]:
                output.append(f"\x1b[{index + 1};1H\x1b[2K" + row)
        self.stream.write("".join(output))
        self.stream.flush()
        self.rows, self.size = rows, size


@contextlib.contextmanager
def terminal_mode(stream: TextIO, input_stream: TextIO):
    restore = []
    interactive = stream.isatty() and input_stream.isatty() and os.environ.get("TERM") != "dumb"
    try:
        if interactive and os.name == "nt":
            import ctypes
            import msvcrt
            kernel = ctypes.windll.kernel32
            handle = msvcrt.get_osfhandle(stream.fileno())
            mode = ctypes.c_ulong()
            handle_value = ctypes.c_void_p(handle)
            if kernel.GetConsoleMode(handle_value, ctypes.byref(mode)) and kernel.SetConsoleMode(handle_value, mode.value | 4):
                restore.append(lambda: kernel.SetConsoleMode(handle_value, mode.value))
            else:
                interactive = False
        elif interactive:
            import termios
            import tty
            fd = input_stream.fileno()
            previous = termios.tcgetattr(fd)
            restore.append(lambda: termios.tcsetattr(fd, termios.TCSADRAIN, previous))
            tty.setcbreak(fd)
        if interactive:
            stream.write("\x1b[?1049h\x1b[?25l")
            stream.flush()
        yield interactive
    finally:
        if interactive:
            try:
                stream.write("\x1b[?25h\x1b[?1049l")
                stream.flush()
            except OSError:
                pass
        for action in reversed(restore):
            action()


def wait_for_exit(seconds: float, input_stream: TextIO) -> bool:
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        if os.name == "nt":
            import msvcrt
            if msvcrt.kbhit():
                char = msvcrt.getwch()
                if char in {"\x00", "\xe0"}:
                    msvcrt.getwch()
                elif char.lower() in {"q", "\x1b", "\x03"}:
                    return True
            time.sleep(min(0.05, max(0, deadline - time.monotonic())))
        else:
            available, _, _ = select.select([input_stream], [], [], max(0, deadline - time.monotonic()))
            if available:
                char = os.read(input_stream.fileno(), 1)
                if char in {b"", b"q", b"Q", b"\x1b", b"\x03"}:
                    return True
    return False


def interval_value(value: str) -> float:
    try:
        interval = float(value)
        if not math.isfinite(interval) or not 1 <= interval <= 60:
            raise ValueError
        return interval
    except ValueError as exc:
        raise argparse.ArgumentTypeError("interval must be a finite number from 1 to 60 seconds") from exc


def run_view(collect: Callable, args: argparse.Namespace, *, stream: TextIO, input_stream: TextIO,
             wait: Callable = wait_for_exit, size: Callable = shutil.get_terminal_size) -> int:
    # Legacy Windows pipe encodings may represent the header but not a chosen
    # workplace name. Use a predictable ASCII fallback for any non-UTF-8 sink.
    ascii_only = args.ascii or (stream.encoding or "").lower().replace("-", "").replace("_", "") != "utf8"
    if args.json:
        print(json.dumps(collect(), ensure_ascii=True, sort_keys=True), file=stream)
        return 0
    if args.once or not stream.isatty() or not input_stream.isatty():
        print("\n".join(render(collect(), 100, 60, ascii_only=ascii_only, details=getattr(args, "details", False))), file=stream)
        return 0
    with terminal_mode(stream, input_stream) as interactive:
        if not interactive:
            print("\n".join(render(collect(), 100, 60, ascii_only=ascii_only, details=getattr(args, "details", False))), file=stream)
            return 0
        screen = Screen(stream)
        while True:
            snapshot = collect()
            dimensions = size()
            screen.draw(render(snapshot, *dimensions, ascii_only=ascii_only, details=getattr(args, "details", False), decorative=True), tuple(dimensions))
            interval = args.interval if args.interval is not None else snapshot.get("configuration", {}).get("interval_seconds")
            if interval is None:
                interval = 2 if snapshot["runtime"]["lifecycle"] == "ready" else snapshot.get("default_interval_seconds", 10)
            if wait(interval, input_stream):
                return 0


def command_monitor(args: argparse.Namespace, core: Any) -> int:
    from processforge_core.configuration import ConfigService, ConfigurationError
    from processforge_core.configuration.yaml_store import YamlConfigStore

    workplace = core.resolve_workplace_root(args.workplace)
    configuration = ConfigService(YamlConfigStore(workplace / "configuration.yaml"))

    def collect():
        snapshot = collect_snapshot(workplace, core.PROCESSFORGE_VERSION)
        if snapshot["runtime"]["lifecycle"] != "ready":
            try:
                snapshot["default_interval_seconds"] = configuration.read().config.runtime.metrics.interval_seconds
            except ConfigurationError:
                snapshot["issues"].append("configuration_invalid")
        return snapshot

    try:
        return run_view(collect, args, stream=sys.stdout, input_stream=sys.stdin)
    except (KeyboardInterrupt, BrokenPipeError):
        return 0
    except Exception:  # A viewer failure must not leak raw local state/paths.
        print("FAIL: monitor observation unavailable", file=sys.stderr)
        return 1
