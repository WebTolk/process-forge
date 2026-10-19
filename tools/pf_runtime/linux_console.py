"""Conservative minimization of a dedicated local X11 xterm window.

Only a direct ``xterm -e python ...`` launch is supported. An existing shell,
terminal tab, multiplexer, remote display, or Wayland session is never a target.
The optional xprop/xdotool programs must already be installed. Importing this
module performs no process, filesystem, or desktop operations.
"""

from __future__ import annotations

import os
import re
import shutil
import stat
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path


_COMMAND_TIMEOUT = 1.0
_STATE_CHECKS = 4
_STATE_DELAY = 0.05
_PROCESS_SCAN_LIMIT = 4096
_PROCESS_SCAN_TIMEOUT = 0.5


@dataclass(frozen=True)
class _Terminal:
    window_id: int
    pid: int
    parent_pid: int
    parent_start: int
    device: int


def _window_id(value: str) -> int | None:
    if not re.fullmatch(r"(?:0[xX][0-9a-fA-F]{1,8}|[0-9]{1,10})", value):
        return None
    number = int(value, 16 if value.lower().startswith("0x") else 10)
    return number if 0 < number <= 0xFFFFFFFF else None


def _process_fields(pid: int) -> list[str]:
    value = Path(f"/proc/{pid}/stat").read_text(encoding="ascii")
    return value[value.rindex(")") + 2 :].split()


def _process_stat(pid: int) -> tuple[int, int]:
    """Read parent PID and start ticks, handling parentheses in process names."""
    fields = _process_fields(pid)
    return int(fields[1]), int(fields[19])


def _exclusive_terminal(pid: int, device: int) -> bool:
    """Reject other session/TTY users, including reparented background jobs.

    Restricted or overly large proc views cannot establish ownership. Only a
    process disappearing during the scan is safe to skip; permission errors
    propagate to the caller's fail-closed result.
    """
    own = _process_fields(pid)
    tty_number = int(own[4]) & 0xFFFFFFFF
    major, minor = os.major(device), os.minor(device)
    encoded_device = (minor & 0xFF) | (major << 8) | ((minor & ~0xFF) << 12)
    if not tty_number or tty_number != encoded_device or int(own[3]) != pid:
        return False
    deadline = time.monotonic() + _PROCESS_SCAN_TIMEOUT
    with os.scandir("/proc") as processes:
        for count, entry in enumerate(processes):
            if count >= _PROCESS_SCAN_LIMIT or time.monotonic() > deadline:
                return False
            if not entry.name.isascii() or not entry.name.isdecimal() or int(entry.name) == pid:
                continue
            try:
                fields = _process_fields(int(entry.name))
            except FileNotFoundError:
                continue
            if int(fields[3]) == pid or (int(fields[4]) & 0xFFFFFFFF) == tty_number:
                return False
    return time.monotonic() <= deadline


def _owned_terminal(window_id: int) -> _Terminal | None:
    """Prove a direct, single-program xterm before inspecting any X11 window."""
    streams = (sys.stdin, sys.stdout)
    if any(stream is None or not stream.isatty() for stream in streams):
        return None
    input_fd, output_fd = (stream.fileno() for stream in streams)
    input_stat, output_stat = os.fstat(input_fd), os.fstat(output_fd)
    if not all(stat.S_ISCHR(item.st_mode) for item in (input_stat, output_stat)):
        return None
    if input_stat.st_rdev != output_stat.st_rdev:
        return None

    pid, parent_pid = os.getpid(), os.getppid()
    if os.getsid(0) != pid or os.getpgrp() != pid or os.tcgetpgrp(input_fd) != pid:
        return None
    parent_root = Path(f"/proc/{parent_pid}")
    if parent_root.stat().st_uid != os.geteuid() or os.getuid() != os.geteuid():
        return None
    if (parent_root / "exe").resolve(strict=True).name != "xterm":
        return None
    parent_of_self, _ = _process_stat(pid)
    _, parent_start = _process_stat(parent_pid)
    if parent_of_self != parent_pid:
        return None

    arguments = (parent_root / "cmdline").read_bytes().rstrip(b"\0").split(b"\0")
    try:
        execute_at = arguments.index(b"-e")
    except ValueError:
        return None
    options = arguments[1:execute_at]
    if any(option.startswith(b"-S") or option == b"-into" for option in options):
        return None
    if execute_at + 1 >= len(arguments):
        return None
    program = os.fsdecode(arguments[execute_at + 1])
    executable = shutil.which(program)
    if not executable or not Path(executable).samefile(Path("/proc/self/exe")):
        return None
    children = (parent_root / "task" / str(parent_pid) / "children").read_text(encoding="ascii").split()
    if children != [str(pid)]:
        return None
    if not _exclusive_terminal(pid, input_stat.st_rdev):
        return None
    if os.getppid() != parent_pid or _process_stat(parent_pid)[1] != parent_start:
        return None
    return _Terminal(window_id, pid, parent_pid, parent_start, input_stat.st_rdev)


def _run(arguments: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        arguments,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        encoding="ascii",
        errors="replace",
        env={**os.environ, "LC_ALL": "C"},
        shell=False,
        timeout=_COMMAND_TIMEOUT,
        check=False,
    )


def _properties(xprop: str, window_id: int) -> str | None:
    result = _run([
        xprop, "-id", str(window_id), "_NET_WM_PID", "WM_CLASS", "WM_STATE", "_NET_WM_STATE",
    ])
    return result.stdout if result.returncode == 0 else None


def _matches_window(properties: str, terminal: _Terminal) -> bool:
    window_pid = re.search(r"^_NET_WM_PID\(CARDINAL\) = ([0-9]+)\s*$", properties, re.MULTILINE)
    window_class = re.search(r'^WM_CLASS\(STRING\) = "[^"\r\n]*", "XTerm"\s*$', properties, re.MULTILINE)
    return bool(window_pid and int(window_pid[1]) == terminal.parent_pid and window_class)


def _window_state(properties: str) -> str | None:
    state = re.search(r"^WM_STATE\(WM_STATE\):[ \t]*\n[ \t]+window state: (Normal|Iconic)[ \t]*$", properties, re.MULTILINE)
    return state[1] if state else None


def _is_minimized(properties: str) -> bool:
    hidden = re.search(r"^_NET_WM_STATE\(ATOM\) = (.*)$", properties, re.MULTILINE)
    return bool(_window_state(properties) == "Iconic" and hidden and "_NET_WM_STATE_HIDDEN" in hidden[1].strip().split(", "))


def minimize_console() -> str:
    """Return minimized, unsupported, not_owned, unavailable, or failed.

    A minimization request alone is never success. Both ICCCM Iconic state and
    EWMH HIDDEN state must be observed on the still-owned window afterwards.
    Missing tools or inaccessible process information fail closed.
    """
    if sys.platform != "linux":
        return "unsupported"
    if os.environ.get("WAYLAND_DISPLAY") or os.environ.get("XDG_SESSION_TYPE", "").lower() not in ("", "x11"):
        return "unsupported"
    if any(os.environ.get(name) for name in (
        "SSH_CONNECTION", "SSH_CLIENT", "SSH_TTY", "TMUX", "STY", "ZELLIJ", "ZELLIJ_SESSION_NAME",
    )) or os.environ.get("TERM", "").startswith(("screen", "tmux")):
        return "unavailable"
    if not re.fullmatch(r":[0-9]+(?:\.[0-9]+)?", os.environ.get("DISPLAY", "")):
        return "unavailable"
    try:
        if sys.stdout is None or not sys.stdout.isatty() or sys.stdin is None or not sys.stdin.isatty():
            return "unavailable"
        window_id = _window_id(os.environ.get("WINDOWID", ""))
        if window_id is None:
            return "not_owned"
        terminal = _owned_terminal(window_id)
        if terminal is None:
            return "not_owned"
        xprop, xdotool = shutil.which("xprop"), shutil.which("xdotool")
        if not xprop or not xdotool:
            return "unavailable"
        properties = _properties(xprop, window_id)
        if properties is None:
            return "unavailable"
        if not _matches_window(properties, terminal):
            return "not_owned"
        if _window_state(properties) is None:
            return "unavailable"
        if _owned_terminal(window_id) != terminal:
            return "not_owned"
        if _is_minimized(properties):
            return "minimized"
        result = _run([xdotool, "windowminimize", str(window_id)])
        if result.returncode != 0:
            return "failed"
        for attempt in range(_STATE_CHECKS):
            if attempt:
                time.sleep(_STATE_DELAY)
            properties = _properties(xprop, window_id)
            if properties is None:
                return "failed"
            if not _matches_window(properties, terminal) or _owned_terminal(window_id) != terminal:
                return "not_owned"
            if _is_minimized(properties):
                return "minimized"
        return "failed"
    except (OSError, ValueError, AttributeError, IndexError, UnicodeError):
        return "unavailable"
    except subprocess.SubprocessError:
        return "failed"
