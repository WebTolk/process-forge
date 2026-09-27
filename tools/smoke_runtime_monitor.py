#!/usr/bin/env python3
"""Monitor truth, byte/time bounds, terminal screen state and read-only CLI."""
from __future__ import annotations

import argparse
from contextlib import contextmanager, redirect_stdout
from datetime import datetime, timedelta, timezone
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import io
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import threading
import time
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from pf_runtime import monitor, service  # noqa: E402
import processforge as core  # noqa: E402


class TTY(io.StringIO):
    encoding = "utf-8"

    def isatty(self):
        return True


class Terminal:
    """Independent tiny VT screen model for the renderer's public output."""
    def __init__(self, columns, lines):
        self.resize(columns, lines)

    def resize(self, columns, lines):
        self.columns, self.lines = columns, lines
        self.cells = [[" "] * columns for _ in range(lines)]
        self.row = self.column = 0

    def feed(self, text):
        tokens = re.split(r"(\x1b\[[0-9;]*[HJK])", text)
        for token in tokens:
            if token == "\x1b[2J":
                self.cells = [[" "] * self.columns for _ in range(self.lines)]
            elif token == "\x1b[2K":
                self.cells[self.row] = [" "] * self.columns
            elif token.startswith("\x1b["):
                match = re.fullmatch(r"\x1b\[(\d+);(\d+)H", token)
                assert match, repr(token)
                self.row, self.column = int(match[1]) - 1, int(match[2]) - 1
                assert 0 <= self.row < self.lines and 0 <= self.column < self.columns
            else:
                for char in token:
                    # Render fixtures are ASCII here; wide characters are
                    # independently checked by expected cell counts below.
                    assert ord(char) >= 32 and ord(char) < 127, repr(char)
                    assert self.column < self.columns - 1, "unexpected auto-wrap"
                    self.cells[self.row][self.column] = char
                    self.column += 1

    def rows(self):
        return ["".join(row).rstrip() for row in self.cells]


@contextmanager
def endpoint(mode="ok"):
    paths = []

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_GET(self):
            paths.append(self.path)
            if mode == "hang":
                time.sleep(1.2)
                return
            body = json.dumps({"ready": True, "status": "ready"}).encode()
            self.send_response(302 if mode == "redirect" else 200)
            self.send_header("Content-Length", str(5000 if mode == "oversize" else len(body)))
            self.end_headers()
            try:
                if mode == "trickle":
                    for char in body:
                        self.wfile.write(bytes([char]))
                        self.wfile.flush()
                        time.sleep(0.2)
                else:
                    self.wfile.write(body)
            except OSError:  # The deadline probe intentionally closes the socket.
                pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}", paths
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def hashes(root):
    return {p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in root.rglob("*") if p.is_file()}


def main():
    # Native PID observation avoids process-list subprocess startup latency.
    assert monitor.pid_alive(os.getpid()) is True
    child = subprocess.Popen([sys.executable, "-B", "-c", "pass"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    child.wait(timeout=10)
    assert monitor.pid_alive(child.pid) is False
    if os.name == "nt":
        import ctypes
        from types import SimpleNamespace
        from unittest.mock import Mock
        opened, wait, close = Mock(return_value=42), Mock(return_value=258), Mock(return_value=1)
        kernel = SimpleNamespace(OpenProcess=opened, WaitForSingleObject=wait, CloseHandle=close)
        with patch.object(ctypes, "WinDLL", return_value=kernel):
            assert monitor.pid_alive(123) is True
            wait.assert_called_with(42, 0)
            close.assert_called_with(42)
            wait.return_value = 0
            assert monitor.pid_alive(123) is False
            wait.return_value = 0xFFFFFFFF
            assert monitor.pid_alive(123) is None
            opened.return_value = 0
            with patch.object(ctypes, "get_last_error", return_value=5):
                assert monitor.pid_alive(123) is None
            with patch.object(ctypes, "get_last_error", return_value=87):
                assert monitor.pid_alive(123) is False
    groups = []
    now = datetime.now(timezone.utc)
    with tempfile.TemporaryDirectory(prefix="pf-monitor-") as raw:
        root = Path(raw)
        workplace = root / "workplace"
        runtime = service.runtime_root(workplace)
        runtime.mkdir(parents=True)
        host = workplace / "runtime" / "pf-runtime-host"
        host.mkdir()

        def write(state, lock=None, cache=None):
            service.service_path(workplace).write_text(json.dumps(state), encoding="utf-8")
            service.lock_path(workplace).write_text(json.dumps(lock if lock is not None else {"pid": os.getpid(), "instance_id": "test"}), encoding="utf-8")
            (host / "state.json").write_text(json.dumps(cache if cache is not None else {"projects": [{"project_root": "PRIVATE_CANARY"}], "sessions": {"secret_session_id": {}}, "updated_at": now.isoformat()}), encoding="utf-8")

        state = {"schema_version": 1, "pid": os.getpid(), "instance_id": "test", "status": "ready", "health": "degraded",
                 "endpoint": "http://127.0.0.1:1", "updated_at": now.isoformat(), "runtime_version": "1.0.0-poc",
                 "token": "PRIVATE_CANARY", "last_scheduler_error": "PRIVATE_CANARY",
                 "scheduler": {"jobs": {"worker": {"last_result": "ok", "last_run": now.isoformat()}}}}
        write(state)
        collect = lambda: monitor.collect_snapshot(workplace, "1.1.0", now=now, alive=lambda pid: True, probe=lambda url: (True, "ready"))
        before = hashes(root)
        snapshot = collect()
        assert snapshot["runtime"]["lifecycle"] == "ready" and snapshot["runtime"]["health"] == "degraded"
        assert snapshot["registrations"]["projects"] == 1 and snapshot["registrations"]["sessions"] == 1
        assert all(value is None for value in snapshot["activity"].values())
        assert "PRIVATE_CANARY" not in json.dumps(snapshot) and "secret_session_id" not in json.dumps(snapshot)
        assert hashes(root) == before and not service.token_path(workplace).exists()
        groups.append("allowlist, cached counts, unknown coverage, no writes")

        for stamp, expected in [(None, "unknown"), ("bad", "unknown"), ((now + timedelta(seconds=1)).isoformat(), "unknown"),
                                ((now - timedelta(seconds=16)).isoformat(), "stale")]:
            write({**state, "updated_at": stamp})
            item = collect()
            assert item["state_freshness"]["status"] == expected and item["runtime"]["health"] == "unknown"
        write(state)
        item = monitor.collect_snapshot(workplace, "1.1.0", now=now, alive=lambda pid: None)
        assert item["runtime"]["lifecycle"] == "unknown"

        def race(url):
            write({**state, "instance_id": "changed"})
            return True, "ready"

        item = monitor.collect_snapshot(workplace, "1.1.0", now=now, alive=lambda pid: True, probe=race)
        assert "owner_changed" in item["issues"] and item["runtime"]["lifecycle"] == "unknown"
        for value in [[], "wrong", {"health": [], "scheduler": {"jobs": {"bad": {"last_result": []}}}}]:
            write(value)
            collect()  # malformed optional fields must not crash
        write(state)
        service.service_path(workplace).write_bytes(b"{" + b" " * monitor.STATE_LIMIT)
        assert collect()["runtime"]["lifecycle"] == "unknown"
        write(state)
        (host / "state.json").write_text("[", encoding="utf-8")
        assert collect()["registrations"]["sessions"] is None
        groups.append("freshness, malformed/oversize, PID failure, owner race")

        # Independent expected lifecycle table preserves existing singleton semantics.
        shared = {"pid": 3, "instance_id": "x", "status": "ready"}
        table = [(shared, shared, True, True, True, True, "ready"),
                 (shared, shared, True, True, True, False, "failed"),
                 (shared, {}, False, False, True, False, "orphaned"),
                 ({}, shared, True, True, False, False, "orphaned"),
                 ({}, {}, True, False, False, False, "orphaned"),
                 ({"status": "stopped"}, {}, False, False, False, False, "stopped"),
                 ({}, {}, False, False, False, False, "not_running"),
                 (shared, shared, True, False, False, False, "stale")]
        for data, lock, exists, pid, state_pid, ready, expected in table:
            assert service.classify_lifecycle(data, lock, lock_exists=exists, pid_running=pid, state_pid_running=state_pid, ready=ready) == expected
        groups.append("shared ownership classification")

        for url in ["https://127.0.0.1:1", "http://example.invalid:1", "http://127.0.0.1:1@192.0.2.1:1", "http://127.0.0.1:1/other", "http://127.0.0.1:1?x=1", None]:
            assert monitor.probe_ready(url) == (None, "endpoint_rejected")
        for mode, expected in [("ok", True), ("redirect", None), ("oversize", None), ("hang", None), ("trickle", None)]:
            with endpoint(mode) as (url, paths):
                start = time.monotonic()
                ready, reason = monitor.probe_ready(url)
                assert ready is expected, (mode, reason)
                assert time.monotonic() - start < 1.5, mode
                assert paths == ["/readyz"]
        groups.append("loopback-only HTTP, no redirects, slow response deadline")

        write(state)
        snapshot = collect()
        snapshot["workplace"] = "test\x1b[2J\r\n\u202e"
        assert "\x1b" not in "\n".join(monitor.render(snapshot)) and "\u202e" not in "\n".join(monitor.render(snapshot))
        assert monitor.cell_width(monitor.crop("界界x", 4)) == 4
        assert monitor.crop("e\u0301x", 1) == "e\u0301"
        assert monitor.crop("界", 2, ascii_only=True) == "?"
        output = io.StringIO()
        screen = monitor.Screen(output)
        previous = 0
        for columns, lines in [(100, 28), (35, 9), (100, 28), (12, 4), (2, 2)]:
            term = Terminal(columns, lines)
            rows = monitor.render(snapshot, columns, lines, ascii_only=True)
            screen.draw(rows, (columns, lines))
            emitted = output.getvalue()[previous:]
            previous = len(output.getvalue())
            term.feed(emitted)
            assert term.rows()[:len(rows)] == [row.rstrip() for row in rows]
            assert all(not row for row in term.rows()[len(rows):])
            if lines > 3:
                assert rows[0].startswith("Runtime")
            # Shorter changed rows and deleted rows must not leave old cells.
            short = [rows[0][:3]]
            screen.draw(short, (columns, lines))
            term.feed(output.getvalue()[previous:])
            previous = len(output.getvalue())
            assert term.rows()[0] == short[0] and all(not row for row in term.rows()[1:])
            screen.draw(short, (columns, lines))
            assert len(output.getvalue()) == previous, "unchanged frame should not flicker"
        groups.append("terminal injection, cell widths, screen resize and cleared tails")

        args = argparse.Namespace(json=False, once=False, ascii=True, no_color=True, interval=1.0)
        screen_stream = TTY()
        with patch.object(monitor, "terminal_mode") as mode:
            mode.return_value.__enter__.return_value = True
            monitor.run_view(collect, args, stream=screen_stream, input_stream=TTY(), wait=lambda *_: True, size=lambda: (50, 15))
            assert mode.return_value.__exit__.called
        with patch.object(monitor, "terminal_mode") as mode:
            mode.return_value.__enter__.return_value = True
            try:
                monitor.run_view(lambda: (_ for _ in ()).throw(KeyboardInterrupt()), args, stream=TTY(), input_stream=TTY())
            except KeyboardInterrupt:
                pass
            assert mode.return_value.__exit__.called
        # Exercise actual terminal cleanup code with minimal platform mode shims.
        if os.name != "nt":
            import termios
            with patch.object(termios, "tcgetattr", return_value=[0, 0, 0, 0, 0, 0, [0]*32]), patch.object(termios, "tcsetattr"):
                input_tty = TTY()
                input_tty.fileno = lambda: 0
                output_tty = TTY()
                try:
                    with monitor.terminal_mode(output_tty, input_tty):
                        raise RuntimeError("fixture")
                except RuntimeError:
                    pass
                assert output_tty.getvalue().endswith("\x1b[?25h\x1b[?1049l")
        else:
            import ctypes
            import msvcrt
            from types import SimpleNamespace
            changes = []

            def get_mode(handle, pointer):
                ctypes.cast(pointer, ctypes.POINTER(ctypes.c_ulong))[0] = 1
                return 1

            kernel = SimpleNamespace(GetConsoleMode=get_mode, SetConsoleMode=lambda handle, mode: changes.append(mode) or 1)
            output_tty = TTY()
            output_tty.fileno = lambda: 1
            with patch.object(ctypes.windll, "kernel32", kernel), patch.object(msvcrt, "get_osfhandle", return_value=1), patch.dict(os.environ, {"TERM": "xterm"}):
                try:
                    with monitor.terminal_mode(output_tty, TTY()) as enabled:
                        assert enabled
                        raise RuntimeError("fixture")
                except RuntimeError:
                    pass
            assert changes == [5, 1] and output_tty.getvalue().endswith("\x1b[?25h\x1b[?1049l")
            with patch.object(msvcrt, "kbhit", return_value=True), patch.object(msvcrt, "getwch", return_value="q"):
                assert monitor.wait_for_exit(1, TTY())
            with patch.object(msvcrt, "kbhit", return_value=True), patch.object(msvcrt, "getwch", return_value="\x03"):
                assert monitor.wait_for_exit(1, TTY())
        groups.append("interactive exit and exception cleanup")

        # Full CLI, existing loopback endpoint, no startup or workplace mutation.
        with endpoint() as (url, paths):
            write({**state, "endpoint": url, "updated_at": datetime.now(timezone.utc).isoformat()})
            before = hashes(root)
            command = [sys.executable, "-B", str(ROOT / "tools/processforge.py"), "monitor", "--workplace", str(workplace)]
            for flags in [["--json"], ["--once", "--ascii", "--no-color"], []]:
                result = subprocess.run(command + flags, cwd=ROOT, capture_output=True, text=True, encoding="utf-8", timeout=12)
                assert result.returncode == 0, result.stderr
                assert "\x1b" not in result.stdout and "PRIVATE_CANARY" not in result.stdout
                if "--json" in flags:
                    assert json.loads(result.stdout)["runtime"]["lifecycle"] == "ready", result.stdout
                assert hashes(root) == before
            assert paths == ["/readyz"] * 3
            for value in ["nan", "inf", "0", "61"]:
                result = subprocess.run(command + ["--interval", value], capture_output=True, text=True, timeout=12)
                assert result.returncode == 2 and result.stdout == ""
            result = subprocess.run([sys.executable, "-B", str(ROOT / "tools/processforge.py"), "--diagnostic-profile", "trace", "--diagnostic-sink", "both", "monitor", "--workplace", str(workplace), "--json"], cwd=ROOT, capture_output=True, text=True, timeout=12)
            assert result.returncode == 0, result.stderr
            assert result.stderr == "" and hashes(root) == before
            with patch.object(core.diagnostics, "for_project", side_effect=AssertionError("viewer attempted diagnostic writes")), redirect_stdout(io.StringIO()) as captured:
                assert core.main(["monitor", "--workplace", str(workplace), "--json"]) == 0
                assert json.loads(captured.getvalue())["kind"] == "pf.runtime.monitor"
            assert hashes(root) == before
        missing = root / "absent"
        result = subprocess.run([sys.executable, "-B", str(ROOT / "tools/processforge.py"), "monitor", "--workplace", str(missing), "--json"], capture_output=True, text=True, timeout=12)
        assert result.returncode == 0 and json.loads(result.stdout)["runtime"]["lifecycle"] == "not_running"
        assert not missing.exists()
        groups.append("real CLI JSON/plain/non-TTY/offline, no files or tokens created")
    for group in groups:
        print("PASS:", group)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
