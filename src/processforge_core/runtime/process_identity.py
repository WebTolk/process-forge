"""OS birth identity without PID-only ownership or unproved tree absence."""

from __future__ import annotations

import ctypes
import socket
import sys
from collections.abc import Callable
from ctypes import wintypes
from pathlib import Path
from typing import Literal

from ..executions.model import ExecutionError, ProcessIdentity


def _linux_identity(
    pid: int, host_id: str, tree_id: str | None
) -> ProcessIdentity | None:
    try:
        boot = (
            Path("/proc/sys/kernel/random/boot_id").read_text(encoding="ascii").strip()
        )
        stat = Path(f"/proc/{pid}/stat").read_text(encoding="ascii")
        # comm may contain spaces and parentheses; fields after its final ')'
        # start at field 3 (state), making starttime (field 22) index 19.
        fields = stat[stat.rindex(")") + 2 :].split()
        ticks = fields[19]
        if not boot or not ticks.isdecimal() or int(ticks) < 1:
            raise ValueError("invalid process birth")
        return ProcessIdentity(
            host_id, boot, pid, "linux-start-ticks:" + ticks, tree_id
        )
    except FileNotFoundError:
        # An unavailable proc filesystem or boot identity is unknown, not death.
        if not Path("/proc/sys/kernel/random/boot_id").is_file():
            raise ExecutionError("execution_activity_unknown") from None
        return None
    except (OSError, ValueError, IndexError):
        raise ExecutionError("execution_activity_unknown") from None


def _windows_identity(
    pid: int, host_id: str, tree_id: str | None
) -> ProcessIdentity | None:
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.OpenProcess.argtypes = (wintypes.DWORD, wintypes.BOOL, wintypes.DWORD)
    kernel.OpenProcess.restype = wintypes.HANDLE
    kernel.GetProcessTimes.argtypes = (
        wintypes.HANDLE,
        ctypes.POINTER(wintypes.FILETIME),
        ctypes.POINTER(wintypes.FILETIME),
        ctypes.POINTER(wintypes.FILETIME),
        ctypes.POINTER(wintypes.FILETIME),
    )
    kernel.GetProcessTimes.restype = wintypes.BOOL
    kernel.CloseHandle.argtypes = (wintypes.HANDLE,)
    kernel.CloseHandle.restype = wintypes.BOOL
    handle = kernel.OpenProcess(0x1000, False, pid)  # QUERY_LIMITED_INFORMATION
    if not handle:
        # ERROR_INVALID_PARAMETER is the documented nonexistent PID case.
        if ctypes.get_last_error() == 87:
            return None
        raise ExecutionError("execution_activity_unknown")
    try:
        creation, exit_time, system, user = (wintypes.FILETIME() for _ in range(4))
        if not kernel.GetProcessTimes(
            handle,
            ctypes.byref(creation),
            ctypes.byref(exit_time),
            ctypes.byref(system),
            ctypes.byref(user),
        ):
            raise ExecutionError("execution_activity_unknown")
        birth = (creation.dwHighDateTime << 32) | creation.dwLowDateTime
        if birth <= 0:
            raise ExecutionError("execution_activity_unknown")
        return ProcessIdentity(
            host_id, None, pid, f"windows-creation-filetime:{birth}", tree_id
        )
    finally:
        kernel.CloseHandle(handle)


def capture_process(pid: int, *, tree_id: str | None = None) -> ProcessIdentity | None:
    """Capture OS creation identity; None proves only this root PID is absent.

    The caller may supply a separately verified owned job/group identity. Merely
    capturing a process never claims that its descendants are owned or absent.
    """
    if type(pid) is not int or not 1 <= pid <= 0xFFFFFFFF:
        raise ValueError("invalid pid")
    host_id = socket.gethostname()
    if sys.platform == "win32":
        return _windows_identity(pid, host_id, tree_id)
    if sys.platform.startswith("linux"):
        return _linux_identity(pid, host_id, tree_id)
    raise ExecutionError("execution_activity_unknown")


def probe_process(identity: ProcessIdentity) -> Literal["same", "absent", "unknown"]:
    """Compare exact host/boot/birth identity, detecting PID reuse safely."""
    if identity.host_id != socket.gethostname():
        return "unknown"
    try:
        observed = capture_process(identity.pid, tree_id=identity.tree_id)
    except (ExecutionError, OSError):
        return "unknown"
    return "same" if observed == identity else "absent"


def tree_absence(
    identity: ProcessIdentity,
    *,
    owned_tree_probe: Callable[[ProcessIdentity], bool | None] | None = None,
) -> bool | None:
    """Require a verified owned-tree probe; root death alone stays unknown.

    The probe must validate an existing handle/job/group or all owned descendant
    identities, and return None when observation is denied or ownership changes.
    """
    root = probe_process(identity)
    if root == "same":
        return False
    if root == "unknown" or identity.tree_id is None or owned_tree_probe is None:
        return None
    try:
        return owned_tree_probe(identity)
    except (ExecutionError, OSError):
        return None
