"""Explicit recovery of one authenticated, unmanaged Windows App Server owner.

This is an operator lifecycle action, not native enrollment or migration proof.
The process handle stays open from observation through termination and waiting.
"""

from __future__ import annotations

import ctypes
import hashlib
import hmac
import json
import math
import os
import stat
import sys
from collections.abc import Callable
from contextlib import AbstractContextManager
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit


class OwnedShutdownError(OSError):
    """Refuse a force recovery whose exact live owner cannot be established."""


def _require(condition: bool, reason: str) -> None:
    if not condition:
        raise OwnedShutdownError(reason)


@dataclass(frozen=True)
class _Owner:
    pid: int
    instance_id: str
    endpoint: str
    started_at: str


def _owner(
    state: dict[str, Any],
    lock: dict[str, Any],
    workplace: Path,
    token: str,
) -> _Owner:
    pid = state.get("pid")
    instance = state.get("instance_id")
    endpoint = state.get("endpoint")
    started_at = state.get("started_at")
    if (
        type(pid) is not int
        or not isinstance(instance, str)
        or not isinstance(endpoint, str)
        or not isinstance(started_at, str)
    ):
        raise OwnedShutdownError("runtime_owner_changed")
    _require(
        pid > 0
        and pid != os.getpid()
        and bool(instance)
        and bool(started_at)
        and state.get("status") == "ready"
        and lock.get("pid") == pid
        and lock.get("instance_id") == instance,
        "runtime_owner_changed",
    )
    selected = Path(str(state.get("workplace_root") or ""))
    _require(
        selected.is_absolute() and selected.resolve(strict=True) == workplace,
        "runtime_workplace_changed",
    )
    expected_hash = "sha256:" + hashlib.sha256(token.encode("utf-8")).hexdigest()
    supplied_hash = state.get("token_hash")
    _require(
        bool(token)
        and isinstance(supplied_hash, str)
        and hmac.compare_digest(supplied_hash, expected_hash),
        "runtime_owner_authentication_failed",
    )
    parsed = urlsplit(endpoint)
    _require(
        parsed.scheme == "http"
        and parsed.hostname in {"127.0.0.1", "::1"}
        and parsed.port is not None
        and parsed.port > 0
        and parsed.username is None
        and parsed.password is None
        and parsed.path in {"", "/"}
        and not parsed.query
        and not parsed.fragment,
        "runtime_endpoint_unqualified",
    )
    return _Owner(pid, instance, endpoint.rstrip("/"), started_at)


@dataclass(frozen=True)
class _ProcessFacts:
    pid: int
    image: Path
    creation: int
    arguments: tuple[str, ...]


class _WindowsProcess:
    """Retain the actual process object; never terminate by a numeric PID."""

    def __init__(self, pid: int) -> None:
        from ctypes import wintypes as w

        self.pid = pid
        self.handle: int | None = None
        self.kernel: Any = ctypes.WinDLL("kernel32", use_last_error=True)
        self.native: Any = ctypes.WinDLL("ntdll", use_last_error=True)
        self.shell: Any = ctypes.WinDLL("shell32", use_last_error=True)
        self.kernel.OpenProcess.argtypes = [w.DWORD, w.BOOL, w.DWORD]
        self.kernel.OpenProcess.restype = w.HANDLE
        self.kernel.CloseHandle.argtypes = [w.HANDLE]
        self.kernel.CloseHandle.restype = w.BOOL
        self.kernel.GetProcessId.argtypes = [w.HANDLE]
        self.kernel.GetProcessId.restype = w.DWORD
        self.kernel.GetProcessTimes.argtypes = [
            w.HANDLE,
            *([ctypes.POINTER(w.FILETIME)] * 4),
        ]
        self.kernel.GetProcessTimes.restype = w.BOOL
        self.kernel.QueryFullProcessImageNameW.argtypes = [
            w.HANDLE,
            w.DWORD,
            w.LPWSTR,
            ctypes.POINTER(w.DWORD),
        ]
        self.kernel.QueryFullProcessImageNameW.restype = w.BOOL
        self.kernel.WaitForSingleObject.argtypes = [w.HANDLE, w.DWORD]
        self.kernel.WaitForSingleObject.restype = w.DWORD
        self.kernel.TerminateProcess.argtypes = [w.HANDLE, w.UINT]
        self.kernel.TerminateProcess.restype = w.BOOL
        self.native.NtQueryInformationProcess.argtypes = [
            w.HANDLE,
            w.ULONG,
            ctypes.c_void_p,
            w.ULONG,
            ctypes.POINTER(w.ULONG),
        ]
        self.native.NtQueryInformationProcess.restype = w.LONG
        self.shell.CommandLineToArgvW.argtypes = [
            w.LPCWSTR,
            ctypes.POINTER(ctypes.c_int),
        ]
        self.shell.CommandLineToArgvW.restype = ctypes.POINTER(w.LPWSTR)
        self.kernel.LocalFree.argtypes = [ctypes.c_void_p]
        self.kernel.LocalFree.restype = ctypes.c_void_p

    def __enter__(self) -> _WindowsProcess:
        # PROCESS_TERMINATE | PROCESS_QUERY_LIMITED_INFORMATION | SYNCHRONIZE.
        handle = self.kernel.OpenProcess(0x101001, False, self.pid)
        _require(bool(handle), "runtime_process_handle_unavailable")
        self.handle = int(handle)
        try:
            _require(self.alive(), "runtime_process_exited")
        except BaseException:
            self.kernel.CloseHandle(self.handle)
            self.handle = None
            raise
        return self

    def __exit__(self, *_exception: Any) -> None:
        if self.handle is not None:
            self.kernel.CloseHandle(self.handle)
            self.handle = None

    def alive(self) -> bool:
        _require(self.handle is not None, "runtime_process_handle_unavailable")
        result = self.kernel.WaitForSingleObject(self.handle, 0)
        _require(result in {0, 258}, "runtime_process_wait_failed")
        return result == 258

    def _arguments(self) -> tuple[str, ...]:
        from ctypes import wintypes as w

        class UnicodeString(ctypes.Structure):
            _fields_ = [
                ("length", w.USHORT),
                ("maximum", w.USHORT),
                ("buffer", ctypes.c_void_p),
            ]

        needed = w.ULONG()
        self.native.NtQueryInformationProcess(
            self.handle, 60, None, 0, ctypes.byref(needed)
        )
        _require(
            ctypes.sizeof(UnicodeString) <= needed.value <= 262144,
            "runtime_command_line_unavailable",
        )
        storage = ctypes.create_string_buffer(needed.value)
        status = self.native.NtQueryInformationProcess(
            self.handle, 60, storage, needed.value, ctypes.byref(needed)
        )
        _require(status == 0, "runtime_command_line_unavailable")
        value = UnicodeString.from_buffer(storage)
        address = value.buffer or 0
        lower = ctypes.addressof(storage)
        _require(
            value.length > 0
            and value.length % 2 == 0
            and value.length <= value.maximum
            and lower + ctypes.sizeof(UnicodeString) <= address
            and address + value.length <= lower + ctypes.sizeof(storage),
            "runtime_command_line_unqualified",
        )
        command = ctypes.wstring_at(address, value.length // 2)
        count = ctypes.c_int()
        arguments = self.shell.CommandLineToArgvW(command, ctypes.byref(count))
        _require(bool(arguments), "runtime_command_line_unavailable")
        try:
            _require(4 <= count.value <= 32, "runtime_command_line_unqualified")
            return tuple(arguments[index] for index in range(count.value))
        finally:
            self.kernel.LocalFree(ctypes.cast(arguments, ctypes.c_void_p))

    def facts(self) -> _ProcessFacts:
        from ctypes import wintypes as w

        _require(self.alive(), "runtime_process_exited")
        _require(
            self.kernel.GetProcessId(self.handle) == self.pid,
            "runtime_process_identity_changed",
        )
        created, exited, kernel_time, user_time = (w.FILETIME() for _ in range(4))
        _require(
            bool(
                self.kernel.GetProcessTimes(
                    self.handle,
                    ctypes.byref(created),
                    ctypes.byref(exited),
                    ctypes.byref(kernel_time),
                    ctypes.byref(user_time),
                )
            ),
            "runtime_process_identity_unavailable",
        )
        creation = (created.dwHighDateTime << 32) | created.dwLowDateTime
        _require(creation > 0, "runtime_process_identity_unavailable")
        image = ctypes.create_unicode_buffer(32768)
        length = w.DWORD(len(image))
        _require(
            bool(
                self.kernel.QueryFullProcessImageNameW(
                    self.handle, 0, image, ctypes.byref(length)
                )
            ),
            "runtime_process_image_unavailable",
        )
        result = _ProcessFacts(
            self.pid,
            Path(image.value).resolve(strict=True),
            creation,
            self._arguments(),
        )
        _require(self.alive(), "runtime_process_exited")
        return result

    def terminate(self, expected: _ProcessFacts, timeout: float) -> None:
        _require(self.facts() == expected, "runtime_process_identity_changed")
        _require(
            bool(self.kernel.TerminateProcess(self.handle, 1)),
            "runtime_process_termination_failed",
        )
        milliseconds = min(0xFFFFFFFE, max(1, math.ceil(timeout * 1000)))
        _require(
            self.kernel.WaitForSingleObject(self.handle, milliseconds) == 0,
            "runtime_process_did_not_stop",
        )


def _target_core(facts: _ProcessFacts, workplace: Path) -> Path:
    from processforge_core.maintenance.file_update import require_unmanaged_target
    from processforge_core.maintenance.update import CoreUpdateError

    _require(
        facts.image == Path(sys.executable).resolve(strict=True),
        "runtime_process_image_unqualified",
    )
    arguments = list(facts.arguments)
    _require(
        bool(arguments) and Path(arguments.pop(0)).resolve(strict=True) == facts.image,
        "runtime_command_line_unqualified",
    )
    while arguments and arguments[0] in {"-B", "-I", "-E", "-s", "-u"}:
        arguments.pop(0)
    _require(len(arguments) >= 5, "runtime_command_line_unqualified")
    script = Path(arguments.pop(0))
    _require(
        script.is_absolute()
        and script.parts[-2:] == ("tools", "processforge.py")
        and arguments.pop(0) in {"runtime", "server"}
        and arguments.pop(0) in {"serve", "run"},
        "runtime_command_line_unqualified",
    )
    options: dict[str, str] = {}
    while arguments:
        option = arguments.pop(0)
        if option in {"--console", "--minimized"}:
            continue
        _require(
            option in {"--workplace", "--port", "--interval"}
            and option not in options
            and bool(arguments),
            "runtime_command_line_unqualified",
        )
        options[option] = arguments.pop(0)
    selected = Path(options.get("--workplace", ""))
    _require(
        selected.is_absolute() and selected.resolve(strict=True) == workplace,
        "runtime_workplace_changed",
    )
    try:
        target = require_unmanaged_target(script.parent.parent)
    except CoreUpdateError:
        raise OwnedShutdownError("runtime_target_not_unmanaged") from None
    for path in (script, script.parent):
        info = path.lstat()
        _require(
            not stat.S_ISLNK(info.st_mode)
            and not getattr(info, "st_file_attributes", 0) & 0x400,
            "runtime_process_entry_unqualified",
        )
    info = script.lstat()
    _require(
        stat.S_ISREG(info.st_mode) and info.st_nlink == 1,
        "runtime_process_entry_unqualified",
    )
    manifest = target / "processforge-core.manifest.json"
    info = manifest.lstat()
    _require(
        stat.S_ISREG(info.st_mode)
        and info.st_nlink == 1
        and not getattr(info, "st_file_attributes", 0) & 0x400,
        "runtime_process_entry_unqualified",
    )
    rows = json.loads(manifest.read_bytes()).get("files", [])
    expected = [
        row for row in rows if row.get("relative_path") == "tools/processforge.py"
    ]
    _require(
        len(expected) == 1
        and expected[0].get("sha256")
        == hashlib.sha256(script.read_bytes()).hexdigest(),
        "runtime_process_entry_unqualified",
    )
    return target


def force_ready_owner_stop(
    workplace_root: Path,
    initial: dict[str, Any],
    token: str,
    *,
    read_owner: Callable[[], tuple[dict[str, Any], dict[str, Any]]],
    request: Callable[..., tuple[int, dict[str, Any]]],
    critical_section: Callable[[], AbstractContextManager[Any]],
    timeout: float,
) -> None:
    """Stop only an exact ready owner after the caller's authenticated 409.

    Caller qualification and fresh owner/handle checks are independent from
    the rejected server admission. No guard, epoch, grant or tree is repaired.
    """
    from pf_native_control import current_entry

    _require(os.name == "nt", "runtime_force_recovery_platform_unsupported")
    _require(math.isfinite(timeout) and timeout > 0, "runtime_stop_timeout_invalid")
    entry = current_entry()
    if (
        entry is None
        or entry.publication is None
        or entry.image is None
        or entry.control is not None
    ):
        raise OwnedShutdownError(
            "runtime_force_recovery_requires_sealed_file_installer"
        )
    image = entry.image
    _require(
        initial.get("kind") == "ready" and initial.get("matching") is True,
        "runtime_owner_changed",
    )
    try:
        workplace = workplace_root.resolve(strict=True)
        expected = _owner(initial["state"], initial["lock"], workplace, token)
        with _WindowsProcess(expected.pid) as process:
            facts = process.facts()
            target = _target_core(facts, workplace)
            caller = entry.root.resolve(strict=True)
            _require(
                image.root == caller
                and caller != target
                and caller not in target.parents
                and target not in caller.parents,
                "runtime_force_recovery_requires_external_installer",
            )
            with critical_section():
                state, lock = read_owner()
                _require(
                    _owner(state, lock, workplace, token) == expected,
                    "runtime_owner_changed",
                )
                code, status = request(
                    "GET", expected.endpoint + "/status", token=token, timeout=timeout
                )
                _require(code == 200, "runtime_owner_authentication_failed")
                _require(
                    _owner(status, lock, workplace, token) == expected,
                    "runtime_owner_changed",
                )
                _require(process.facts() == facts, "runtime_process_identity_changed")
                _require(
                    _target_core(facts, workplace) == target, "runtime_owner_changed"
                )
                state, lock = read_owner()
                _require(
                    _owner(state, lock, workplace, token) == expected,
                    "runtime_owner_changed",
                )
                process.terminate(facts, timeout)
    except OwnedShutdownError:
        raise
    except (OSError, ValueError, TypeError, KeyError, AttributeError):
        raise OwnedShutdownError("runtime_force_recovery_unqualified") from None
