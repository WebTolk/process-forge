"""Native process containment before any worker target code can execute.

This stdlib-only leaf does not load Core or discover installation authority.
Windows jobs prohibit breakaway and travel with an inherited kernel handle.
"""

from __future__ import annotations

import ast
import ctypes
import hashlib
import io
import json
import logging
import os
import re
import stat
import subprocess
import sys
import threading
import time
import unicodedata
from collections.abc import Callable, Iterator, Mapping
from contextlib import AbstractContextManager, ExitStack, contextmanager
from contextvars import ContextVar
from ctypes import wintypes
from dataclasses import dataclass, field
from pathlib import Path
from types import FrameType, MappingProxyType
from typing import TYPE_CHECKING, Any, BinaryIO
from uuid import uuid4

if TYPE_CHECKING:
    from pf_linux_native_control import OwnedNamespace

_PHYSICAL_OPEN = io.open
_MODULE_CODE = sys._getframe().f_code


class NativeControlError(OSError):
    """Refuse an operation whose exact native ownership cannot be established."""

    def __init__(self) -> None:
        self.code = "execution_activity_unknown"
        super().__init__("execution_activity_unknown")


def _kernel() -> Any:
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    signatures = (
        ("CreateJobObjectW", (ctypes.c_void_p, wintypes.LPCWSTR), wintypes.HANDLE),
        (
            "OpenJobObjectW",
            (wintypes.DWORD, wintypes.BOOL, wintypes.LPCWSTR),
            wintypes.HANDLE,
        ),
        (
            "SetInformationJobObject",
            (wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD),
            wintypes.BOOL,
        ),
        (
            "QueryInformationJobObject",
            (
                wintypes.HANDLE,
                ctypes.c_int,
                ctypes.c_void_p,
                wintypes.DWORD,
                ctypes.c_void_p,
            ),
            wintypes.BOOL,
        ),
        ("AssignProcessToJobObject", (wintypes.HANDLE, wintypes.HANDLE), wintypes.BOOL),
        (
            "IsProcessInJob",
            (wintypes.HANDLE, wintypes.HANDLE, ctypes.c_void_p),
            wintypes.BOOL,
        ),
        ("TerminateJobObject", (wintypes.HANDLE, wintypes.UINT), wintypes.BOOL),
        ("GetCurrentProcess", (), wintypes.HANDLE),
        (
            "DuplicateHandle",
            (
                wintypes.HANDLE,
                wintypes.HANDLE,
                wintypes.HANDLE,
                ctypes.c_void_p,
                wintypes.DWORD,
                wintypes.BOOL,
                wintypes.DWORD,
            ),
            wintypes.BOOL,
        ),
        ("CloseHandle", (wintypes.HANDLE,), wintypes.BOOL),
        ("CreateToolhelp32Snapshot", (wintypes.DWORD, wintypes.DWORD), wintypes.HANDLE),
        ("Thread32First", (wintypes.HANDLE, ctypes.c_void_p), wintypes.BOOL),
        ("Thread32Next", (wintypes.HANDLE, ctypes.c_void_p), wintypes.BOOL),
        (
            "OpenThread",
            (wintypes.DWORD, wintypes.BOOL, wintypes.DWORD),
            wintypes.HANDLE,
        ),
        ("GetProcessIdOfThread", (wintypes.HANDLE,), wintypes.DWORD),
        ("ResumeThread", (wintypes.HANDLE,), wintypes.DWORD),
        (
            "GetProcessTimes",
            (
                wintypes.HANDLE,
                ctypes.c_void_p,
                ctypes.c_void_p,
                ctypes.c_void_p,
                ctypes.c_void_p,
            ),
            wintypes.BOOL,
        ),
        (
            "OpenProcess",
            (wintypes.DWORD, wintypes.BOOL, wintypes.DWORD),
            wintypes.HANDLE,
        ),
    )
    for name, arguments, result in signatures:
        function = getattr(kernel, name)
        function.argtypes, function.restype = arguments, result
    return kernel


class _Limits(ctypes.Structure):
    _fields_ = [
        ("process_time", ctypes.c_int64),
        ("job_time", ctypes.c_int64),
        ("flags", wintypes.DWORD),
        ("minimum", ctypes.c_size_t),
        ("maximum", ctypes.c_size_t),
        ("active", wintypes.DWORD),
        ("affinity", ctypes.c_size_t),
        ("priority", wintypes.DWORD),
        ("scheduling", wintypes.DWORD),
    ]


class _Extended(ctypes.Structure):
    _fields_ = [
        ("basic", _Limits),
        ("io", ctypes.c_uint64 * 6),
        ("memory", ctypes.c_size_t * 4),
    ]


class _Accounting(ctypes.Structure):
    _fields_ = [
        ("times", ctypes.c_int64 * 4),
        ("faults", wintypes.DWORD),
        ("total", wintypes.DWORD),
        ("active", wintypes.DWORD),
        ("terminated", wintypes.DWORD),
    ]


class _Thread(ctypes.Structure):
    _fields_ = [
        ("size", wintypes.DWORD),
        ("usage", wintypes.DWORD),
        ("id", wintypes.DWORD),
        ("owner", wintypes.DWORD),
        ("base", wintypes.LONG),
        ("delta", wintypes.LONG),
        ("flags", wintypes.DWORD),
    ]


def _birth(kernel: Any, handle: Any) -> str:
    creation, exited, system, user = (wintypes.FILETIME() for _ in range(4))
    if not kernel.GetProcessTimes(
        handle,
        ctypes.byref(creation),
        ctypes.byref(exited),
        ctypes.byref(system),
        ctypes.byref(user),
    ):
        raise NativeControlError()
    return str((creation.dwHighDateTime << 32) | creation.dwLowDateTime)


def _resume_initial_thread(kernel: Any, pid: int) -> None:
    # Popen closes CreateProcess's initial thread handle. The suspended process
    # has not run user code; retain its sole exact thread before resuming it.
    snapshot = kernel.CreateToolhelp32Snapshot(4, 0)
    if snapshot in (None, ctypes.c_void_p(-1).value):
        raise NativeControlError()
    threads: list[int] = []
    try:
        entry = _Thread()
        entry.size = ctypes.sizeof(entry)
        valid = kernel.Thread32First(snapshot, ctypes.byref(entry))
        while valid:
            if entry.owner == pid:
                threads.append(int(entry.id))
            valid = kernel.Thread32Next(snapshot, ctypes.byref(entry))
    finally:
        kernel.CloseHandle(snapshot)
    if len(threads) != 1:
        raise NativeControlError()
    handle = kernel.OpenThread(0x0002 | 0x0800, False, threads[0])
    if not handle:
        raise NativeControlError()
    try:
        if (
            kernel.GetProcessIdOfThread(handle) != pid
            or kernel.ResumeThread(handle) != 1
        ):
            raise NativeControlError()
    finally:
        kernel.CloseHandle(handle)


class OwnedJob:
    """Retain a named non-breakaway Job and query the whole native process set."""

    def __init__(self, handle: Any, name: str) -> None:
        self.handle, self.name = handle, name
        self.kernel = _kernel()

    @classmethod
    def create(cls, token: str | None = None) -> OwnedJob:
        value = token or uuid4().hex
        if len(value) != 32 or any(c not in "0123456789abcdef" for c in value):
            raise NativeControlError()
        name = "Local\\pf-execution-" + value
        kernel = _kernel()
        ctypes.set_last_error(0)
        handle = kernel.CreateJobObjectW(None, name)
        if not handle:
            raise NativeControlError()
        job = cls(handle, name)
        try:
            if ctypes.get_last_error() == 183:
                raise NativeControlError()
            limits = _Extended()
            limits.basic.flags = 0x2000  # KILL_ON_JOB_CLOSE, no breakaway flags.
            if not kernel.SetInformationJobObject(
                handle, 9, ctypes.byref(limits), ctypes.sizeof(limits)
            ):
                raise NativeControlError()
            return job
        except BaseException:
            job.close()
            raise

    def __del__(self) -> None:
        self.close()

    def active(self) -> int:
        facts = _Accounting()
        if not self.handle or not self.kernel.QueryInformationJobObject(
            self.handle, 1, ctypes.byref(facts), ctypes.sizeof(facts), None
        ):
            raise NativeControlError()
        return int(facts.active)

    def stop(self, *, deadline: float) -> bool:
        if not self.kernel.TerminateJobObject(self.handle, 130):
            raise NativeControlError()
        while self.active():
            if time.monotonic() >= deadline:
                return False
            time.sleep(min(0.01, max(0, deadline - time.monotonic())))
        return True

    def close(self) -> None:
        if self.handle:
            self.kernel.CloseHandle(self.handle)
            self.handle = None


def inherited_job(environment: dict[str, str]) -> OwnedJob | None:
    """Validate an inherited handle against current process membership."""
    handle_text = environment.get("PF_NATIVE_JOB_HANDLE")
    name = environment.get("PF_NATIVE_JOB_NAME", "")
    if handle_text is None and not name:
        return None
    if (
        not handle_text
        or not handle_text.isdecimal()
        or not name.startswith("Local\\pf-execution-")
    ):
        raise NativeControlError()
    handle = int(handle_text)
    kernel = _kernel()
    member = wintypes.BOOL()
    if (
        not kernel.IsProcessInJob(
            kernel.GetCurrentProcess(), handle, ctypes.byref(member)
        )
        or not member.value
    ):
        raise NativeControlError()
    job = OwnedJob(handle, name)
    _INHERITED_JOBS.append(job)
    return job


_INHERITED_JOBS: list[OwnedJob] = []


def _windows_batch_command(argv: list[str]) -> tuple[str, str]:
    """Quote a batch shim and its forwarded CRT argv for both CMD parses.

    Popen's sequence conversion quotes for the C runtime, not CMD. A batch
    shim then reparses its arguments when forwarding %*, so arguments need
    two layers of CMD escaping. Keep delayed expansion and AutoRun disabled.
    """
    # Physical line breaks cannot be safely represented in a CMD invocation.
    # Refuse rather than treating argument data as a second command.
    if any(any(character in value for character in "\x00\r\n") for value in argv):
        raise ValueError("batch arguments contain unsupported control characters")
    interpreter = str(Path(os.environ["SystemRoot"]) / "System32" / "cmd.exe")
    metacharacters = re.compile(r'([()\[\]%!^"`<>&|;, *?\t])')

    def escape(value: str) -> str:
        return metacharacters.sub(r"^\1", value)

    arguments = []
    for argument in argv[1:]:
        # Always quote, including empty strings and metacharacters without
        # whitespace. Double backslashes before quotes and the closing quote
        # according to the Windows CRT argument rules.
        quoted = re.sub(r'(\\*)"', r'\1\1\\"', argument)
        quoted = re.sub(r"(\\*)$", r"\1\1", quoted)
        arguments.append(escape(escape('"' + quoted + '"')))
    body = " ".join([escape(argv[0]), *arguments])
    command = subprocess.list2cmdline([interpreter]) + ' /d /s /v:off /c "' + body + '"'
    return interpreter, command


def spawn_owned(
    argv: list[str],
    *,
    token: str | None = None,
    receipt_path: Path | None = None,
    identity: dict[str, Any] | None = None,
    independent: bool = False,
    **options: Any,
) -> subprocess.Popen[bytes]:
    """Assign a suspended child to its retained Job before its first instruction.

    A duplicate Job handle is inherited by exactly the launched root. Therefore
    abrupt controller death cannot leave a wrapper without a containment fence.
    Child death closes that handle; last-handle close kills remaining members.
    On Linux, independent=True requests a new ephemeral namespace even inside
    an inherited owner; durable token/receipt/identity inputs are then refused.
    """
    if type(independent) is not bool:
        raise TypeError("independent must be a bool")
    if sys.platform.startswith("linux"):
        from pf_linux_native_control import spawn

        return spawn(
            argv,
            token=token,
            receipt_path=receipt_path,
            identity=identity,
            independent=independent,
            **options,
        )
    if os.name != "nt":
        if independent:
            raise NativeControlError()
        # A POSIX process group is useful for signalling but is not a complete
        # descendant ownership primitive. No positive tree proof is exported.
        options.setdefault("start_new_session", True)
        return subprocess.Popen(argv, **options)
    job = OwnedJob.create(token)
    duplicate = wintypes.HANDLE()
    kernel = job.kernel
    process: subprocess.Popen[bytes] | None = None
    try:
        current = kernel.GetCurrentProcess()
        if not kernel.DuplicateHandle(
            current, job.handle, current, ctypes.byref(duplicate), 0, True, 2
        ):
            raise NativeControlError()
        supplied_environment = options.pop("env", None)
        environment = dict(
            os.environ if supplied_environment is None else supplied_environment
        )
        # Do not inherit another attempt's handle pointer.
        environment["PF_NATIVE_JOB_HANDLE"] = str(duplicate.value)
        environment["PF_NATIVE_JOB_NAME"] = job.name
        startup = subprocess.STARTUPINFO()
        startup.lpAttributeList = {"handle_list": [duplicate.value]}
        options["startupinfo"] = startup
        options["close_fds"] = True
        options["creationflags"] = (
            int(options.get("creationflags", 0)) | 4
        )  # CREATE_SUSPENDED
        command: str | list[str] = argv
        if argv and Path(argv[0]).suffix.lower() in {".cmd", ".bat"}:
            executable, command = _windows_batch_command(argv)
            options["executable"] = executable
            options["shell"] = False
        process = subprocess.Popen(command, env=environment, **options)
        if not kernel.AssignProcessToJobObject(
            job.handle, int(getattr(process, "_handle"))
        ):
            raise NativeControlError()
        facts = {
            "schema_version": 1,
            "pid": process.pid,
            "birth_id": _birth(kernel, int(getattr(process, "_handle"))),
            "job_name": job.name,
            "identity": identity or {},
        }
        if receipt_path is not None:
            receipt_path.parent.mkdir(parents=True, exist_ok=True)
            temporary = receipt_path.with_name(
                "." + receipt_path.name + "." + uuid4().hex
            )
            try:
                temporary.write_text(
                    json.dumps(facts, sort_keys=True) + "\n", encoding="utf-8"
                )
                os.replace(temporary, receipt_path)
            finally:
                temporary.unlink(missing_ok=True)
        setattr(process, "native_job", job)
        setattr(process, "native_facts", facts)
        _resume_initial_thread(kernel, process.pid)
        return process
    except BaseException:
        if process is not None:
            # Exact retained Popen handle, including assignment-failure cases.
            process.kill()
            process.wait(timeout=5)
        job.stop(deadline=time.monotonic() + 5)
        job.close()
        raise
    finally:
        if duplicate.value:
            kernel.CloseHandle(duplicate)


def reopen_job(
    facts: dict[str, Any], *, pid: int, identity: dict[str, Any]
) -> OwnedJob | OwnedNamespace | None:
    """Reopen only exact persisted attempt ownership; PID reuse cannot signal it.

    None means the authenticated non-breakaway Job no longer exists. Any access
    denial or identity mismatch raises; arbitrary legacy PID facts grant nothing.
    """
    if sys.platform.startswith("linux"):
        from pf_linux_native_control import reopen

        return reopen(facts, pid=pid, identity=identity)
    if (
        os.name != "nt"
        or type(pid) is not int
        or type(facts.get("pid")) is not int
        or facts.get("identity") != identity
        or facts.get("pid") != pid
    ):
        raise NativeControlError()
    name = facts.get("job_name")
    birth = facts.get("birth_id")
    if (
        not isinstance(name, str)
        or not name.startswith("Local\\pf-execution-")
        or len(name) != len("Local\\pf-execution-") + 32
        or any(c not in "0123456789abcdef" for c in name[-32:])
        or not isinstance(birth, str)
        or not birth.isdecimal()
        or int(birth) < 1
    ):
        raise NativeControlError()
    kernel = _kernel()
    process = kernel.OpenProcess(0x1000, False, pid)
    root_live = False
    if process:
        try:
            if _birth(kernel, process) != birth:
                raise NativeControlError()
            creation, exited, system, user = (wintypes.FILETIME() for _ in range(4))
            if not kernel.GetProcessTimes(
                process,
                ctypes.byref(creation),
                ctypes.byref(exited),
                ctypes.byref(system),
                ctypes.byref(user),
            ):
                raise NativeControlError()
            root_live = not (exited.dwHighDateTime or exited.dwLowDateTime)
        finally:
            kernel.CloseHandle(process)
    elif ctypes.get_last_error() != 87:
        raise NativeControlError()
    handle = kernel.OpenJobObjectW(4 | 8, False, name)
    if not handle:
        if ctypes.get_last_error() == 2 and not root_live:
            return None
        raise NativeControlError()
    return OwnedJob(handle, name)


# Source image and request leases are deliberately distinct lifetimes. The
# caller must supply accepted pins from its qualified installer handoff.
@contextmanager
def _private_process_open(target: Path) -> Iterator[Any]:
    """Keep Windows writers and replacement excluded while reading private data."""
    if os.name != "nt":
        with _PHYSICAL_OPEN(target, "rb") as stream:
            yield stream
        return
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.CreateFileW.argtypes = (
        wintypes.LPCWSTR,
        wintypes.DWORD,
        wintypes.DWORD,
        ctypes.c_void_p,
        wintypes.DWORD,
        wintypes.DWORD,
        wintypes.HANDLE,
    )
    kernel.CreateFileW.restype = wintypes.HANDLE
    kernel.CloseHandle.argtypes = (wintypes.HANDLE,)
    kernel.CloseHandle.restype = wintypes.BOOL
    # FILE_SHARE_READ only: both existing and later writers/delete handles fail.
    # OPEN_REPARSE_POINT keeps a replaced leaf from redirecting the read handle.
    handle = kernel.CreateFileW(str(target), 0x80000000, 1, None, 3, 0x00200000, None)
    if handle == ctypes.c_void_p(-1).value:
        raise NativeControlError()
    try:
        with _PHYSICAL_OPEN(target, "rb") as stream:
            yield stream
    finally:
        kernel.CloseHandle(handle)


def _private_process_bytes(root: Path, relative: str) -> bytes:
    """Read one private YAML snapshot without admitting code or path aliases."""
    parts = relative.split("/")
    if (
        len(parts) < 3
        or parts[:2] not in (["processes", "user"], ["processes", "custom"])
        or any(part in {"", ".", ".."} for part in parts)
        or any(
            ":" in part
            or "\\" in part
            or part.endswith((" ", "."))
            or any(ord(char) < 32 for char in part)
            for part in parts
        )
        or Path(relative).suffix.lower() not in {".yaml", ".yml"}
    ):
        raise NativeControlError()
    target = root.joinpath(*parts)
    fields = (
        "st_dev",
        "st_ino",
        "st_mode",
        "st_nlink",
        "st_size",
        "st_mtime_ns",
        "st_ctime_ns",
    )

    def checked_stat() -> os.stat_result:
        if target.resolve(strict=True) != target:
            raise NativeControlError()
        for node in (target, *target.parents):
            info = node.lstat()
            if (
                stat.S_ISLNK(info.st_mode)
                or getattr(info, "st_file_attributes", 0) & 0x400
            ):
                raise NativeControlError()
            if node == root:
                break
        info = target.lstat()
        if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
            raise NativeControlError()
        return info

    def signature(info: os.stat_result) -> tuple[int, ...]:
        return tuple(getattr(info, field) for field in fields)

    try:
        before = checked_stat()
        with _private_process_open(target) as stream:
            opened = os.fstat(stream.fileno())
            if signature(before) != signature(opened):
                raise NativeControlError()
            raw = stream.read(before.st_size + 1)
            after = os.fstat(stream.fileno())
            if (
                len(raw) != before.st_size
                or signature(before) != signature(after)
                or signature(before) != signature(checked_stat())
            ):
                raise NativeControlError()
        return raw
    except OSError:
        raise NativeControlError() from None


class NativeImage:
    """Immutable accepted source/resources, including direct spec loaders.

    Capture is noncreating. It never derives expected pins from current source
    files. Core code and published resources use accepted payload bytes; private
    process YAML has a separate checked, read-only data path.
    """

    def __init__(self, root: Path, accepted: dict[str, str]) -> None:
        import hashlib
        from types import MappingProxyType

        self.root = root.resolve(strict=True)
        if not accepted:
            raise NativeControlError()
        files: dict[str, bytes] = {}
        for relative, expected in accepted.items():
            if not isinstance(relative, str) or not isinstance(expected, str):
                raise NativeControlError()
            parts = relative.split("/")
            if (
                not relative
                or any(p in {"", ".", ".."} for p in parts)
                or "\\" in relative
                or ":" in relative
                or "\x00" in relative
            ):
                raise NativeControlError()
            target = self.root.joinpath(*parts)
            for node in (target, *target.parents):
                info = node.lstat()
                if node.is_symlink() or getattr(info, "st_file_attributes", 0) & 0x400:
                    raise NativeControlError()
                if node == self.root:
                    break
            if target.stat().st_nlink != 1:
                raise NativeControlError()
            raw = target.read_bytes()
            if len(expected) != 64 or hashlib.sha256(raw).hexdigest() != expected:
                raise NativeControlError()
            files[relative] = raw
        self.files = MappingProxyType(files)
        self._active = False
        self._source_checkout = False

    def relative(self, value: Any) -> str | None:
        if isinstance(value, int):
            return None
        try:
            path = Path(value).absolute()
            return path.relative_to(self.root).as_posix()
        except (
            TypeError,
            ValueError,
        ):
            return None

    @classmethod
    def from_publication(cls, root: Path, publication: Publication) -> NativeImage:
        """Use the exact verified capture; never reopen code after acceptance."""
        image = cls.__new__(cls)
        image.root = root.resolve(strict=True)
        resources = dict(publication.payload)
        if publication.manifest:
            if digest(publication.manifest) != publication.manifest_sha256:
                raise NativeControlError()
            resources[MANIFEST] = publication.manifest
        image.files = MappingProxyType(resources)
        image._active = False
        image._source_checkout = False
        return image

    def read(self, relative: str) -> bytes:
        try:
            return self.files[relative]
        except KeyError:
            raise NativeControlError() from None

    def activate(self, *, _core_entry: Any = None) -> None:
        """Install lifetime byte loaders before any Core import; no pyc reads."""
        import builtins
        import importlib.abc
        import importlib.machinery
        import importlib.util
        import io
        import locale
        import sys

        if self._active:
            return
        loaded_core = {
            name
            for name in sys.modules
            if name == "processforge_core" or name.startswith("processforge_core.")
        }
        if loaded_core:
            # Only the still-running named entry may precede capture. Its full
            # code must match accepted bytes, and it must be the direct caller
            # of bootstrap_entry now, before its first business import. This
            # never qualifies an already executed module or a direct alias.
            entry_path = str(self.root / "src/processforge_core/__init__.py")
            module = sys.modules.get("processforge_core")
            frame = sys._getframe(1).f_back
            if (
                loaded_core != {"processforge_core"}
                or sys._getframe(1).f_code is not bootstrap_entry.__code__
                or frame is None
                or _core_entry is None
                or _core_entry is not frame
                or frame.f_globals is not getattr(module, "__dict__", None)
                or frame.f_locals is not frame.f_globals
                or getattr(getattr(module, "__spec__", None), "name", None)
                != "processforge_core"
                or getattr(getattr(module, "__spec__", None), "_initializing", False)
                is not True
                or getattr(getattr(module, "__spec__", None), "origin", None)
                != entry_path
                or frame.f_code.co_filename != entry_path
                or frame.f_code
                != compile(
                    self.read("src/processforge_core/__init__.py"),
                    entry_path,
                    "exec",
                    dont_inherit=True,
                )
            ):
                raise NativeControlError()
        image = self
        original_spec = importlib.util.spec_from_file_location
        original_open, original_io_open = builtins.open, io.open
        # PEP 420 packages are part of the accepted image too. Derive their
        # locations solely from captured source paths, never from a disk scan.
        namespaces: dict[str, list[str]] = {}
        for relative in image.files:
            parts = relative.split("/")
            if parts[0] not in {"src", "tools"} or not relative.endswith(".py"):
                continue
            for end in range(2, len(parts)):
                name = ".".join(parts[1:end])
                location = str(image.root.joinpath(*parts[:end]))
                locations = namespaces.setdefault(name, [])
                if location not in locations:
                    locations.append(location)

        class Loader(importlib.abc.Loader):
            def __init__(self, relative: str) -> None:
                self.relative = relative

            def create_module(self, spec: Any) -> None:
                return None

            def exec_module(self, module: Any) -> None:
                code = compile(
                    image.read(self.relative),
                    str(image.root / self.relative),
                    "exec",
                    dont_inherit=True,
                )
                exec(code, module.__dict__)

        class Finder(importlib.abc.MetaPathFinder):
            def find_spec(
                self, fullname: str, path: Any = None, target: Any = None
            ) -> Any:
                module = fullname.replace(".", "/")
                for base in ("src/", "tools/"):
                    for suffix in ("/__init__.py", ".py"):
                        relative = base + module + suffix
                        if relative in image.files:
                            return captured_spec(fullname, image.root / relative)
                if fullname in namespaces:
                    spec = importlib.machinery.ModuleSpec(
                        fullname, None, is_package=True
                    )
                    spec.submodule_search_locations = list(namespaces[fullname])
                    return spec
                physical = importlib.machinery.PathFinder.find_spec(fullname, path)
                if physical is not None:
                    if physical.origin and image.relative(physical.origin) is not None:
                        raise NativeControlError()
                    if physical.submodule_search_locations and any(
                        image.relative(location) is not None
                        for location in physical.submodule_search_locations
                    ):
                        raise NativeControlError()
                return None

        def captured_spec(
            name: str,
            location: Any = None,
            *,
            loader: Any = None,
            submodule_search_locations: Any = None,
        ) -> Any:
            relative = image.relative(location) if location is not None else None
            if relative is None:
                return original_spec(
                    name,
                    location,
                    loader=loader,
                    submodule_search_locations=submodule_search_locations,
                )
            if not relative.endswith(".py"):
                raise NativeControlError()
            image.read(relative)
            package = relative.endswith("/__init__.py")
            locations = (
                [str((image.root / relative).parent)]
                if package
                else submodule_search_locations
            )
            return original_spec(
                name,
                str(image.root / relative),
                loader=Loader(relative),
                submodule_search_locations=locations,
            )

        def captured_open(
            file: Any,
            mode: str = "r",
            buffering: int = -1,
            encoding: str | None = None,
            errors: str | None = None,
            newline: str | None = None,
            closefd: bool = True,
            opener: Any = None,
        ) -> Any:
            relative = image.relative(file)
            report_parts = relative.split("/") if relative is not None else []
            report_output = relative in {
                ".pf/runtime/release-test/latest-report.json",
                ".pf/runtime/release-test/latest-report.md",
                ".pf/runtime/release-test/latest-trace.ndjson",
            } or (
                len(report_parts) == 6
                and report_parts[:4] == [".pf", "runtime", "release-test", "commands"]
                and len(report_parts[4]) == 32
                and all(char in "0123456789abcdef" for char in report_parts[4])
                and report_parts[5] in {"stdout.log", "stderr.log", "result.json"}
            )
            project_state = image._source_checkout and report_parts[:1] == [".pf"]
            if report_output or project_state:
                target = image.root.joinpath(*report_parts)
                # Private project data in a verified source checkout is mutable.
                # Code/spec loaders still require accepted publication bytes.
                # Aliases, symlinks/reparse points and hard links stay failclosed.
                for node in (target, *target.parents):
                    if node.exists() or node.is_symlink():
                        info = node.lstat()
                        if (
                            node.is_symlink()
                            or getattr(info, "st_file_attributes", 0) & 0x400
                            or (node.is_file() and info.st_nlink != 1)
                        ):
                            raise NativeControlError()
                    if node == image.root:
                        break
                if (
                    target.resolve() != target
                    or relative in image.files
                    or (opener is not None and not project_state)
                    or not closefd
                ):
                    raise NativeControlError()
            if (
                relative is None
                or relative.startswith("runtime/")
                or report_output
                or project_state
            ):
                return original_open(
                    file, mode, buffering, encoding, errors, newline, closefd, opener
                )
            if mode not in {"r", "rt", "rb"} or opener is not None or not closefd:
                raise NativeControlError()
            if (
                relative not in image.files
                and len(report_parts) >= 3
                and report_parts[:2] in (["processes", "user"], ["processes", "custom"])
                and Path(relative).suffix.lower() in {".yaml", ".yml"}
            ):
                raw = io.BytesIO(_private_process_bytes(image.root, relative))
            else:
                raw = io.BytesIO(image.read(relative))
            raw.name = str(image.root / relative)
            if mode == "rb":
                if encoding is not None or errors is not None or newline is not None:
                    raise ValueError("binary mode does not take text options")
                return raw
            return io.TextIOWrapper(
                raw,
                encoding=encoding or locale.getencoding(),
                errors=errors,
                newline=newline,
            )

        self._originals = (original_spec, original_open, original_io_open)
        # Metadata-only handshake with optional configuration storage: absence
        # on disk must never hide a captured body. No body/refusal is suppressed.
        setattr(
            captured_open,
            "_pf_captured_path",
            lambda path: image.relative(path) in image.files,
        )
        self._finder = Finder()
        sys.meta_path.insert(0, self._finder)
        importlib.util.spec_from_file_location = captured_spec
        builtins.open = captured_open
        io.open = captured_open
        sys.dont_write_bytecode = True
        self._active = True


class NativeControl:
    """Request-scoped shared lease with a bounded accepted epoch check.

    Existing guard/epoch paths and accepted epoch come from the trusted native
    installer/child handoff. This class never initializes them or treats a
    missing prior-installation exclusion baseline as proof.
    """

    def __init__(self, guard: Path, epoch_path: Path, accepted_epoch: str) -> None:
        if not accepted_epoch or len(accepted_epoch.encode("ascii")) > 256:
            raise NativeControlError()
        self.guard, self.epoch_path, self.accepted_epoch = (
            guard,
            epoch_path,
            accepted_epoch,
        )

    def operation(
        self, *, deadline: float | None = None
    ) -> AbstractContextManager[NativeControl]:
        """Acquire a shared lease for a live request, releasing it on all exits."""
        return self._lease(False, deadline)

    def exclusive(
        self, *, deadline: float | None = None
    ) -> AbstractContextManager[NativeControl]:
        """Acquire only after old scopes unwind; no lock upgrade is supported."""
        return self._lease(True, deadline)

    def _lease(
        self, exclusive: bool, deadline: float | None
    ) -> AbstractContextManager[NativeControl]:
        from contextlib import contextmanager

        @contextmanager
        def held() -> Iterator[NativeControl]:
            lock_pid = os.getpid()
            # A live shared scope cannot be upgraded or silently replaced.
            if _CONTROL_LEASE.get() is not None:
                raise NativeControlError()
            stop = deadline if deadline is not None else time.monotonic() + 30
            if time.monotonic() >= stop:
                raise NativeControlError()
            try:
                stream = self.guard.open("r+b", buffering=0)
            except OSError:
                raise NativeControlError() from None
            locked = False
            token = None
            life = None
            life_token = None
            exclusive_token = None
            try:
                if sys.platform == "win32":
                    import msvcrt

                    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
                    kernel.LockFileEx.argtypes = (
                        wintypes.HANDLE,
                        wintypes.DWORD,
                        wintypes.DWORD,
                        wintypes.DWORD,
                        wintypes.DWORD,
                        ctypes.c_void_p,
                    )
                    kernel.LockFileEx.restype = wintypes.BOOL
                    kernel.UnlockFileEx.argtypes = (
                        wintypes.HANDLE,
                        wintypes.DWORD,
                        wintypes.DWORD,
                        wintypes.DWORD,
                        ctypes.c_void_p,
                    )
                    kernel.UnlockFileEx.restype = wintypes.BOOL

                    # OVERLAPPED: pointer-sized Internal/InternalHigh, offsets,
                    # then hEvent. Zero initialization means byte offset zero.
                    class Overlapped(ctypes.Structure):
                        _fields_ = [
                            ("internal", ctypes.c_size_t),
                            ("high", ctypes.c_size_t),
                            ("offset", wintypes.DWORD),
                            ("offset_high", wintypes.DWORD),
                            ("event", wintypes.HANDLE),
                        ]

                    overlapped = Overlapped()
                    handle = msvcrt.get_osfhandle(stream.fileno())
                    while not kernel.LockFileEx(
                        handle,
                        1 | (2 if exclusive else 0),
                        0,
                        1,
                        0,
                        ctypes.byref(overlapped),
                    ):
                        if ctypes.get_last_error() != 33 or time.monotonic() >= stop:
                            raise NativeControlError()
                        time.sleep(min(0.005, max(0, stop - time.monotonic())))
                else:
                    import fcntl

                    while True:
                        if os.getpid() != lock_pid:
                            raise NativeControlError()
                        try:
                            fcntl.flock(
                                stream.fileno(),
                                (fcntl.LOCK_EX if exclusive else fcntl.LOCK_SH)
                                | fcntl.LOCK_NB,
                            )
                            break
                        except BlockingIOError:
                            if time.monotonic() >= stop:
                                raise NativeControlError()
                            time.sleep(min(0.005, max(0, stop - time.monotonic())))
                locked = True
                if os.getpid() != lock_pid:
                    raise NativeControlError()
                with self.epoch_path.open("rb") as epoch:
                    raw = epoch.read(257)
                if (
                    len(raw) > 256
                    or raw.decode("ascii") != self.accepted_epoch
                    or time.monotonic() >= stop
                ):
                    raise NativeControlError()
                if os.getpid() != lock_pid:
                    raise NativeControlError()
                token = _CONTROL_LEASE.set(self)
                guard_info = os.fstat(stream.fileno())
                life = _OperationLifetime(
                    lock_pid,
                    threading.get_ident(),
                    exclusive=exclusive,
                    guard_fd=stream.fileno(),
                    guard_identity=(guard_info.st_dev, guard_info.st_ino),
                )
                life_token = _OPERATION_LIFETIME.set(life)
                if exclusive:
                    exclusive_token = _EXCLUSIVE_LIFETIMES.set(
                        (*_EXCLUSIVE_LIFETIMES.get(), (self, life))
                    )
                yield self
            except (
                OSError,
                UnicodeError,
            ):
                if token is None:
                    raise NativeControlError() from None
                raise
            finally:
                if life is not None:
                    life.active = False
                if exclusive_token is not None:
                    _EXCLUSIVE_LIFETIMES.reset(exclusive_token)
                if life_token is not None:
                    _OPERATION_LIFETIME.reset(life_token)
                if token is not None:
                    _CONTROL_LEASE.reset(token)
                # POSIX fork inherits the same open-file description. A child
                # may close its duplicate, but LOCK_UN would unlock its parent.
                if locked and lock_pid == os.getpid():
                    if sys.platform == "win32":
                        kernel.UnlockFileEx(handle, 0, 1, 0, ctypes.byref(overlapped))
                    else:
                        fcntl.flock(stream.fileno(), fcntl.LOCK_UN)
                stream.close()

        return held()


_CONTROL_LEASE: ContextVar[NativeControl | None] = ContextVar(
    "pf_native_control_lease", default=None
)


@dataclass
class _OperationLifetime:
    pid: int
    thread_id: int
    active: bool = True
    exclusive: bool = False
    guard_fd: int | None = None
    guard_identity: tuple[int, int] | None = None


_OPERATION_LIFETIME: ContextVar[_OperationLifetime | None] = ContextVar(
    "pf_native_operation_lifetime", default=None
)

# Private producer/publication scopes can temporarily replace the current
# operation while the independent outer OS lock is still held. Retain only
# lifetimes minted by the actual exclusive lock path, never caller identities.
_EXCLUSIVE_LIFETIMES: ContextVar[
    tuple[tuple[NativeControl, _OperationLifetime], ...]
] = ContextVar("pf_native_exclusive_lifetimes", default=())


# PF:PUBLICATION:BEGIN
_PUBLICATION_SEAL = None
# PF:PUBLICATION:END

LEAF = "tools/pf_native_control.py"
MANIFEST = "processforge-core.manifest.json"
INVENTORY = "checksums/processforge.sha256"
SEAL_KIND = "pf.publication.v1"
BEGIN = b"# PF:PUBLICATION:BEGIN\n"
END = b"# PF:PUBLICATION:END\n"
MAX_MANIFEST = 8 * 1024 * 1024
MAX_FILE = 128 * 1024 * 1024
MAX_TOTAL = 512 * 1024 * 1024
HEX = re.compile(r"[0-9a-f]{64}\Z")


class Refusal(ValueError):
    """Signal private refusal; callers map this to existing envelopes."""


def digest(raw: bytes) -> str:
    """Hash exact bytes."""
    return hashlib.sha256(raw).hexdigest()


def canonical_release_bytes(raw: bytes) -> bytes:
    """Match the observed release_file_content transform before freezing."""
    return raw if b"\0" in raw else raw.replace(b"\r\n", b"\n")


def canonical_json(value: Any) -> bytes:
    """Produce the versioned ASCII JSON projection encoding."""
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False
    ).encode("ascii")


def safe_path(value: Any) -> str:
    """Reject ambiguous POSIX/Windows paths before mapping or opening."""
    if not isinstance(value, str) or not value or value.startswith("/"):
        raise Refusal("unsafe_path")
    if unicodedata.normalize("NFC", value) != value:
        raise Refusal("noncanonical_path")
    if any(ord(c) < 32 or ord(c) == 127 or c in '\\:<>"|?*' for c in value):
        raise Refusal("unsafe_path")
    reserved = {"con", "prn", "aux", "nul", "conin$", "conout$"}
    reserved.update(f"{p}{i}" for p in ("com", "lpt") for i in range(1, 10))
    for part in value.split("/"):
        if (
            part in {"", ".", ".."}
            or part.endswith((".", " "))
            or part.split(".")[0].casefold() in reserved
        ):
            raise Refusal("unsafe_path")
    return value


def _unique_paths(paths: list[str]) -> None:
    folded: set[str] = set()
    for path in paths:
        safe_path(path)
        key = path.casefold()
        if key in folded:
            raise Refusal("duplicate_path")
        folded.add(key)
    for path in folded:
        parts = path.split("/")
        if any("/".join(parts[:i]) in folded for i in range(1, len(parts))):
            raise Refusal("file_directory_collision")


def _pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise Refusal("duplicate_json_key")
        result[key] = value
    return result


def _no_number(value: str) -> Any:
    raise Refusal("unsupported_json_number")


def parse_manifest(raw: bytes) -> dict[str, Any]:
    """Strictly parse the actual Core v1 shape, before any dict overwrite."""
    if len(raw) > MAX_MANIFEST:
        raise Refusal("manifest_limit")
    try:
        data = json.loads(
            raw.decode("utf-8"),
            object_pairs_hook=_pairs,
            parse_float=_no_number,
            parse_constant=_no_number,
        )
    except (UnicodeError, ValueError, RecursionError) as exc:
        raise Refusal("manifest_json") from exc
    keys = {"schema_version", "kind", "version", "source", "generated_at", "files"}
    if not isinstance(data, dict) or set(data) != keys:
        raise Refusal("manifest_shape")
    if type(data["schema_version"]) is not int or data["schema_version"] != 1:
        raise Refusal("manifest_schema")
    if data["kind"] != "processforge.core_manifest":
        raise Refusal("manifest_kind")
    if not isinstance(data["source"], dict):
        raise Refusal("manifest_source")
    for key in ("version", "generated_at"):
        if not isinstance(data[key], str) or not data[key]:
            raise Refusal("manifest_metadata")
    rows = data["files"]
    if not isinstance(rows, list) or not rows:
        raise Refusal("manifest_files")
    paths: list[str] = []
    for row in rows:
        if not isinstance(row, dict) or set(row) != {"relative_path", "size", "sha256"}:
            raise Refusal("manifest_entry")
        path = safe_path(row["relative_path"])
        if path == MANIFEST or path.lower().endswith((".pyc", ".pyo")):
            raise Refusal("excluded_or_bytecode_entry")
        if type(row["size"]) is not int or not 0 <= row["size"] <= MAX_FILE:
            raise Refusal("manifest_size")
        if not isinstance(row["sha256"], str) or not HEX.fullmatch(row["sha256"]):
            raise Refusal("manifest_digest")
        paths.append(path)
    _unique_paths(paths)
    if (
        not {LEAF, INVENTORY}.issubset(paths)
        or sum(row["size"] for row in rows) > MAX_TOTAL
    ):
        raise Refusal("leaf_missing_or_total_limit")
    return data


def projection(raw_manifest: bytes) -> bytes:
    """Exclude leaf and derived inventory; both are checked separately.

    The observed inventory hashes the leaf. Including its row here would
    restore a transitive seal -> leaf -> inventory -> seal hash cycle.
    """
    data = parse_manifest(raw_manifest)
    data["files"] = sorted(
        (row for row in data["files"] if row["relative_path"] not in {LEAF, INVENTORY}),
        key=lambda row: row["relative_path"],
    )
    return canonical_json({"projection_schema": 1, "manifest": data})


def _block(source: bytes) -> tuple[bytes, bytes, bytes] | None:
    if BEGIN not in source and END not in source:
        return None
    if source.count(BEGIN) != 1 or source.count(END) != 1:
        raise Refusal("seal_markers")
    before, rest = source.split(BEGIN)
    if END not in rest:
        raise Refusal("seal_marker_order")
    body, after = rest.split(END)
    return before, body, after


def leaf_seal(trusted_leaf: bytes) -> tuple[str, str] | None:
    """Read literal data from already trusted source; never execute a loader."""
    parts = _block(trusted_leaf)
    if parts is None:
        return None
    try:
        tree = ast.parse(parts[1].decode("ascii"))
        if len(tree.body) != 1 or not isinstance(tree.body[0], ast.Assign):
            raise Refusal("seal_assignment")
        node = tree.body[0]
        if (
            len(node.targets) != 1
            or not isinstance(node.targets[0], ast.Name)
            or node.targets[0].id != "_PUBLICATION_SEAL"
        ):
            raise Refusal("seal_assignment")
        value = ast.literal_eval(node.value)
    except (UnicodeError, SyntaxError, ValueError) as exc:
        raise Refusal("seal_literal") from exc
    if value is None:
        return None
    if not isinstance(value, tuple) or len(value) != 2:
        raise Refusal("seal_shape")
    kind, pin = value
    if not isinstance(kind, str) or not isinstance(pin, str):
        raise Refusal("seal_shape")
    if kind != SEAL_KIND:
        return None
    if not HEX.fullmatch(pin):
        raise Refusal("seal_digest")
    return kind, pin


def _sealed_leaf(source: bytes, pin: str) -> bytes:
    parts = _block(source)
    if parts is None:
        raise Refusal("build_requires_seal_slot")
    leaf_seal(source)
    body = f'_PUBLICATION_SEAL = ("{SEAL_KIND}", "{pin}")\n'.encode("ascii")
    result = parts[0] + BEGIN + body + END + parts[2]
    compile(result, LEAF, "exec", dont_inherit=True)
    return result


def _manifest(
    payload: Mapping[str, bytes],
    *,
    version: str,
    source: Mapping[str, Any],
    generated_at: str,
) -> bytes:
    data = {
        "schema_version": 1,
        "kind": "processforge.core_manifest",
        "version": version,
        "generated_at": generated_at,
        "source": dict(source),
        "files": [
            {"relative_path": path, "size": len(raw), "sha256": digest(raw)}
            for path, raw in sorted(payload.items())
        ],
    }
    raw = (json.dumps(data, indent=2, sort_keys=True, allow_nan=False) + "\n").encode()
    parse_manifest(raw)
    return raw


def inventory_bytes(payload: Mapping[str, bytes]) -> bytes:
    """Match shipped checksum lines; leaf is fully hashed, inventory excluded.

    Integration must retain the observed public_file_entries/release selection
    parity check. No Core manifest is an inventory entry in the current code.
    """
    return "".join(
        f"{digest(raw)}  {path}\n"
        for path, raw in sorted(payload.items())
        if path not in {INVENTORY, MANIFEST}
    ).encode("utf-8")


@dataclass(frozen=True)
class Build:
    """Hold exactly the immutable entries to write to a future ZIP."""

    payload: Mapping[str, bytes]
    manifest: bytes
    projection_sha256: str


def build_publication(
    payload: Mapping[str, bytes],
    *,
    version: str,
    source: Mapping[str, Any],
    generated_at: str,
) -> Build:
    """Seal a frozen canonical byte staging; never write source or an archive."""
    frozen = dict(payload)
    _unique_paths(list(frozen))
    if LEAF not in frozen or MANIFEST in frozen:
        raise Refusal("build_payload")
    if any(not isinstance(raw, bytes) for raw in frozen.values()):
        raise Refusal("build_requires_bytes")
    if INVENTORY not in frozen:
        raise Refusal("build_requires_inventory")
    provisional = _manifest(
        frozen, version=version, source=source, generated_at=generated_at
    )
    pin = digest(projection(provisional))
    frozen[LEAF] = _sealed_leaf(frozen[LEAF], pin)
    frozen[INVENTORY] = inventory_bytes(frozen)
    final = _manifest(frozen, version=version, source=source, generated_at=generated_at)
    if digest(projection(final)) != pin:
        raise Refusal("cyclic_build")
    return Build(MappingProxyType(frozen), final, pin)


def _read_bounded(stream: BinaryIO, limit: int) -> bytes:
    """Retain bounded file bytes without allocating the caller's full ceiling."""
    chunks: list[bytes] = []
    size = 0
    while True:
        chunk = stream.read(min(64 * 1024, limit + 1 - size))
        if not chunk:
            return b"".join(chunks)
        size += len(chunk)
        if size > limit:
            raise Refusal("read_limit")
        chunks.append(chunk)


def _read_regular(root: Path, relative: str, limit: int) -> bytes:
    path = root
    for part in ("", *relative.split("/")):
        if part:
            path = path / part
        info = path.lstat()
        if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & 0x400:
            raise Refusal("link_or_reparse_point")
    if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
        raise Refusal("not_regular")
    with _PHYSICAL_OPEN(path, "rb") as stream:
        raw = _read_bounded(stream, limit)
    if len(raw) > limit:
        raise Refusal("read_limit")
    return raw


@dataclass(frozen=True)
class Publication:
    """Accepted immutable image inputs; full manifest digest is only metadata."""

    payload: Mapping[str, bytes]
    projection_sha256: str
    manifest_sha256: str
    manifest: bytes = b""


def accept_publication(root: Path, *, trusted_leaf: bytes) -> Publication | None:
    """Verify before Core, outside guard; None keeps recognized legacy mode.

    No guard/epoch/runtime directory is created. Caller validates the physical
    root, supplies the source bytes it compiled as the trusted leaf, and retains
    the returned bytes for all loads. This proves content, never operational
    exclusion; managed callers still require their actual deployment leases.
    A caller-supplied current-file pin is not a trust source for this function.
    """
    return _capture_publication(root, trusted_leaf, _read_regular)


def _capture_publication(
    root: Path, trusted_leaf: bytes, read: Callable[[Path, str, int], bytes]
) -> Publication | None:
    """Accept one complete seal-bound byte image using the caller's reader."""
    seal = leaf_seal(trusted_leaf)
    if seal is None:
        return None
    try:
        raw = read(root, MANIFEST, MAX_MANIFEST)
        data = parse_manifest(raw)
        if digest(projection(raw)) != seal[1]:
            raise Refusal("publication_drift")
        captured: dict[str, bytes] = {}
        for row in data["files"]:
            path = row["relative_path"]
            content = trusted_leaf if path == LEAF else read(root, path, row["size"])
            if len(content) != row["size"] or digest(content) != row["sha256"]:
                raise Refusal("payload_drift")
            captured[path] = content
        if captured.get(INVENTORY) != inventory_bytes(captured):
            raise Refusal("derived_inventory_drift")
        return Publication(MappingProxyType(captured), seal[1], digest(raw), raw)
    except OSError as exc:
        raise Refusal("publication_unreadable") from exc


def _snapshot_read_regular(root: Path, relative: str, limit: int) -> bytes:
    """Read through retained no-follow POSIX directories, without path reopen.

    Concurrent replacement can change the directory entries, but cannot retarget
    these descriptors. Every returned byte still has to match the trusted seal.
    This is a content snapshot reader, not a replacement or writer-death lease.
    """
    parts = (*root.parts[1:], *safe_path(relative).split("/"))
    nofollow = int(getattr(os, "O_NOFOLLOW"))
    flags = os.O_RDONLY | int(getattr(os, "O_DIRECTORY")) | nofollow
    with ExitStack() as directories:
        directory = os.open(root.anchor, flags)
        directories.callback(os.close, directory)
        for part in parts[:-1]:
            directory = os.open(part, flags, dir_fd=directory)
            directories.callback(os.close, directory)
        descriptor = os.open(
            parts[-1],
            os.O_RDONLY | nofollow | int(getattr(os, "O_NONBLOCK")),
            dir_fd=directory,
        )
        with os.fdopen(descriptor, "rb") as stream:
            before = os.fstat(stream.fileno())
            if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1:
                raise Refusal("not_regular")
            raw = _read_bounded(stream, limit)
            after = os.fstat(stream.fileno())
        # Reading can update atime; it is not content or alias drift.
        if any(
            getattr(before, key) != getattr(after, key)
            for key in (
                "st_dev",
                "st_ino",
                "st_mode",
                "st_nlink",
                "st_size",
                "st_mtime_ns",
                "st_ctime_ns",
            )
        ):
            raise Refusal("capture_changed")
        if len(raw) > limit:
            raise Refusal("read_limit")
        return raw


def _snapshot_origin(
    root: Path, trusted_leaf: bytes, publication: Publication, caller: FrameType
) -> None:
    """Bind the executing helper and whole entry to this exact captured image."""
    leaf_path = str(root / LEAF)
    module = sys.modules.get("pf_native_control")
    if (
        getattr(module, "__dict__", None) is not globals()
        or globals().get("__file__") != leaf_path
        or globals().get("_captured_source") != trusted_leaf
        or _MODULE_CODE.co_filename != leaf_path
        or _MODULE_CODE != compile(trusted_leaf, leaf_path, "exec", dont_inherit=True)
    ):
        raise NativeControlError()
    for relative in (
        "tools/processforge.py",
        "tools/pf_runtime/mcp_server.py",
        "tools/pf_runtime/codex_hooks.py",
        "tools/pf_runtime/kimi_hooks.py",
        "tools/pf_runtime/service.py",
        "tools/migrate-storage.py",
        "tools/migrate-hook-journals.py",
        "tools/prepared_executor.py",
        "tools/codex_exec_worker.py",
        "src/processforge_core/__init__.py",
    ):
        path = str(root / relative)
        raw = publication.payload.get(relative)
        if (
            raw is not None
            and caller.f_globals.get("__file__") == path
            and caller.f_code.co_filename == path
            and caller.f_code == compile(raw, path, "exec", dont_inherit=True)
        ):
            return
    raise NativeControlError()


@dataclass(frozen=True)
class NativeEntry:
    """Captured publication for one interpreter; leases last only per operation."""

    root: Path
    publication: Publication | None
    image: NativeImage | None
    control: NativeControl | None

    def operation(
        self, *, deadline: float | None = None
    ) -> AbstractContextManager[NativeEntry]:
        """Use existing controls without creating installation state on reads."""
        entry = self

        class Held(AbstractContextManager[NativeEntry]):
            def __init__(self) -> None:
                self.lease: AbstractContextManager[NativeControl] | None = None

            def __enter__(self) -> NativeEntry:
                if entry.control is None:
                    # Unadopted publication grants no migration authority.
                    return entry
                if _CONTROL_LEASE.get() is entry.control:
                    life = _OPERATION_LIFETIME.get()
                    if (
                        life is None
                        or not life.active
                        or life.pid != os.getpid()
                        or life.thread_id != threading.get_ident()
                    ):
                        raise NativeControlError()
                else:
                    lease = entry.control.operation(deadline=deadline)
                    lease.__enter__()
                    self.lease = lease
                return entry

            def __exit__(self, *_exception: Any) -> None:
                if self.lease is not None:
                    # Like request_scope: finish the generator lease without
                    # injecting an exception whose traceback may be frozen.
                    self.lease.__exit__(None, None, None)

        return Held()


_ENTRY: NativeEntry | None = None


def _capture_source_publication(
    root: Path, trusted_leaf: bytes, caller: FrameType
) -> Publication:
    """Verify a source inventory, then seal and recapture only retained bytes.

    The checkout and its inventory are the trusted source input. This portable
    image grants neither enrollment nor historical writer retirement. Nothing
    is published back into the checkout, including the generated seal.
    """

    def source_only() -> None:
        for relative in (MANIFEST, "runtime/native-control", "runtime/managed-ingress"):
            path = root / relative
            if path.exists() or path.is_symlink():
                raise Refusal("source_has_installation_state")

    read = _read_regular if os.name == "nt" else _snapshot_read_regular
    source_only()
    try:
        leaf = canonical_release_bytes(trusted_leaf)
        parts = _block(leaf)
        if parts is None or parts[1].strip() != b"_PUBLICATION_SEAL = None":
            raise Refusal("source_seal_slot")
        if read(root, LEAF, MAX_FILE) != trusted_leaf:
            raise Refusal("source_leaf_drift")
        inventory = canonical_release_bytes(read(root, INVENTORY, MAX_MANIFEST))
        entries: dict[str, str] = {}
        names: list[str] = []
        for line in inventory.decode("utf-8").splitlines():
            expected, separator, name = line.partition("  ")
            if not separator or not HEX.fullmatch(expected):
                raise Refusal("source_inventory_entry")
            names.append(safe_path(name))
            entries[name] = expected
        _unique_paths(names)
        required = {
            LEAF,
            "VERSION",
            "tools/processforge.py",
            "src/processforge_core/__init__.py",
        }
        if (
            not required.issubset(entries)
            or INVENTORY in entries
            or MANIFEST in entries
            or any(name.lower().endswith((".pyc", ".pyo")) for name in entries)
        ):
            raise Refusal("source_inventory_files")
        payload: dict[str, bytes] = {}
        total = 0
        for name, expected in entries.items():
            raw = canonical_release_bytes(read(root, name, MAX_FILE))
            total += len(raw)
            if total > MAX_TOTAL or digest(raw) != expected:
                raise Refusal("source_payload_drift")
            payload[name] = raw
        if payload[LEAF] != leaf or inventory_bytes(payload) != inventory:
            raise Refusal("source_inventory_drift")
        # Bind the executing entry before replacing its leaf seal in memory.
        # A library import cannot promote arbitrary caller code.
        _snapshot_origin(
            root, trusted_leaf, Publication(MappingProxyType(payload), "", ""), caller
        )
        source_only()
        payload[INVENTORY] = inventory
        build = build_publication(
            payload,
            version=payload["VERSION"].decode("utf-8").strip(),
            source={"source_inventory_sha256": digest(inventory)},
            generated_at="source",
        )
        retained = {**build.payload, MANIFEST: build.manifest}

        def captured_read(_root: Path, relative: str, limit: int) -> bytes:
            raw = retained[relative]
            if len(raw) > limit:
                raise Refusal("read_limit")
            return raw

        publication = _capture_publication(root, build.payload[LEAF], captured_read)
        if publication is None:
            raise NativeControlError()
        return publication
    except (OSError, UnicodeError) as exc:
        raise Refusal("source_unreadable") from exc


def bootstrap_entry(
    root: Path, *, trusted_leaf: bytes, _core_entry: Any = None
) -> NativeEntry:
    """Accept captured native source before Core; never use a bytecode loader.

    The trusted entry/interpreter and qualified deployment remain the TCB.
    Publication capture does not attest legacy writer/tree quiescence.
    """
    global _ENTRY
    root = root.absolute()
    if _ENTRY is not None:
        if _ENTRY.root != root:
            raise NativeControlError()
        return _ENTRY
    seal = leaf_seal(trusted_leaf)
    if seal is None and sys._getframe(1).f_globals.get("__name__") != "__main__":
        # Source libraries remain ordinary imports. Only an explicit trusted
        # script entry activates a retained image and native execution capability.
        return NativeEntry(root, None, None, None)
    for path in (root, *root.parents):
        info = path.lstat()
        if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & 0x400:
            raise NativeControlError()
    if seal is None:
        source_publication = _capture_source_publication(
            root, trusted_leaf, sys._getframe(1)
        )
        image = NativeImage.from_publication(root, source_publication)
        if image.root != root:
            raise NativeControlError()
        image._source_checkout = True
        image.activate(_core_entry=_core_entry)
        _ENTRY = NativeEntry(root, source_publication, image, None)
        return _ENTRY
    guard = root / "runtime/native-control/installation.guard"
    epoch = root / "runtime/native-control/epoch"
    if guard.exists() != epoch.exists():
        raise NativeControlError()
    control = _bootstrap_control(root, seal[1], guard, epoch)
    snapshot_only = control is None and os.name != "nt"
    from contextlib import ExitStack

    with ExitStack() as leases:
        if control is not None:
            leases.enter_context(control.operation())
        elif os.name == "nt":
            leases.enter_context(_publication_read_exclusion(root))
        if snapshot_only:
            # A fresh file-only entry needs a complete immutable code image,
            # not an attestation of deployment exclusion. Never promote this
            # snapshot to a control/epoch or a qualified native operation.
            if _snapshot_read_regular(root, LEAF, MAX_FILE) != trusted_leaf:
                raise NativeControlError()
            publication = _capture_publication(
                root, trusted_leaf, _snapshot_read_regular
            )
            if publication is not None:
                _snapshot_origin(root, trusted_leaf, publication, sys._getframe(1))
            if (
                guard.exists() != epoch.exists()
                or _bootstrap_control(root, seal[1], guard, epoch) is not None
            ):
                raise NativeControlError()
        else:
            if _read_regular(root, LEAF, MAX_FILE) != trusted_leaf:
                raise NativeControlError()
            publication = accept_publication(root, trusted_leaf=trusted_leaf)
        if publication is None:
            raise NativeControlError()
        image = NativeImage.from_publication(root, publication)
        if snapshot_only and image.root != root:
            raise NativeControlError()
    image.activate(_core_entry=_core_entry)
    _ENTRY = NativeEntry(root, publication, image, control)
    return _ENTRY


def operation_lease(*, deadline: float | None = None) -> AbstractContextManager[None]:
    """Retain only a live operation, using the already captured native image."""

    class Held(AbstractContextManager[None]):
        def __init__(self) -> None:
            self.scope: AbstractContextManager[NativeEntry] | None = None

        def __enter__(self) -> None:
            entry = current_entry()
            if entry is not None:
                scope = entry.operation(deadline=deadline)
                scope.__enter__()
                self.scope = scope

        def __exit__(self, *_exception: Any) -> None:
            if self.scope is not None:
                self.scope.__exit__(None, None, None)

    return Held()


def current_entry() -> NativeEntry | None:
    """Return the already accepted native entry without discovery or I/O."""
    return _ENTRY


def _log_owned_execution_refusal(reason: str, **facts: Any) -> None:
    # Diagnostics must not turn a fail-closed capability result into an error.
    try:
        _write_owned_execution_refusal(reason, **facts)
    except Exception:
        return


def _write_owned_execution_refusal(reason: str, **facts: Any) -> None:
    """Emit only bounded native facts, never paths, argv, identities or messages."""
    error = facts.pop("error", None)
    failures: list[dict[str, Any]] = []
    while error is not None and len(failures) < 4:
        failure = {
            "type": type(error).__name__,
            "errno": getattr(error, "errno", None),
            "winerror": getattr(error, "winerror", None),
        }
        trace = error.__traceback__
        while trace is not None:
            if trace.tb_frame.f_code.co_filename == __file__:
                failure.update(
                    native_function=trace.tb_frame.f_code.co_name,
                    native_line=trace.tb_lineno,
                )
            trace = trace.tb_next
        failures.append(failure)
        error = error.__cause__ or error.__context__
    logger = logging.getLogger(__name__)
    emit = logger.debug if reason == "job_retired_after_wait" else logger.warning
    emit(
        "PF_NATIVE_CAPABILITY %s",
        json.dumps({"reason": reason, **facts, "failures": failures}, sort_keys=True),
    )


def supports_owned_execution() -> bool:
    """Probe the actual retained whole-tree backend, independently of SQLite.

    Explicit initialization probes real suspended creation/Job attachment. It creates no guard,
    database, UUID metadata or maintenance evidence on an unsupported host.
    """
    if (
        (os.name != "nt" and not sys.platform.startswith("linux"))
        or _ENTRY is None
        or _ENTRY.publication is None
    ):
        _log_owned_execution_refusal(
            "entry_or_platform",
            supported_platform=os.name == "nt" or sys.platform.startswith("linux"),
            entry_present=_ENTRY is not None,
            publication_present=_ENTRY is not None and _ENTRY.publication is not None,
        )
        return False
    probe_facts: dict[str, Any] = {}
    try:
        if sys.platform.startswith("linux"):
            from pf_linux_native_control import inherited

            # Membership is checked against the live kernel namespace, carrier
            # and init identities. It proves this process is already fenced;
            # it grants no independent owner or historical migration authority.
            if inherited(dict(os.environ)) is not None:
                return True
        process = spawn_owned(
            [sys.executable, "-B", "-c", "pass"],
            env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        job = getattr(process, "native_job")
        try:
            started = time.monotonic()
            deadline = started + 5
            returncode = process.wait(timeout=max(0, deadline - time.monotonic()))
            probe_facts["root_wait_ms"] = round((time.monotonic() - started) * 1000, 3)
            if returncode != 0:
                _log_owned_execution_refusal(
                    "child_exit", returncode=returncode, **probe_facts
                )
                return False
            # Root exit does not prove whole-tree retirement. Retain ownership
            # until an empty backend is observed within the same wait budget.
            probe_facts["observations"] = 0
            while True:
                now = time.monotonic()
                probe_facts["elapsed_ms"] = round((now - started) * 1000, 3)
                if now >= deadline:
                    _log_owned_execution_refusal(
                        "job_retirement_timeout", **probe_facts
                    )
                    return False
                active = job.active()
                probe_facts["observations"] += 1
                probe_facts.setdefault("first_active", active)
                probe_facts["active"] = active
                now = time.monotonic()
                probe_facts["elapsed_ms"] = round((now - started) * 1000, 3)
                if now >= deadline:
                    _log_owned_execution_refusal(
                        "job_retirement_timeout", **probe_facts
                    )
                    return False
                if active == 0:
                    _log_owned_execution_refusal(
                        "job_retired_after_wait", **probe_facts
                    )
                    return True
                time.sleep(min(0.01, deadline - now))
        finally:
            try:
                if process.poll() is None:
                    job.stop(deadline=time.monotonic() + 5)
                    process.wait(timeout=5)
            finally:
                job.close()
    except (
        OSError,
        AttributeError,
        ValueError,
        subprocess.SubprocessError,
    ) as error:
        _log_owned_execution_refusal("probe_exception", error=error, **probe_facts)
        return False


@contextmanager
def _publication_read_exclusion(root: Path) -> Iterator[None]:
    """Retain read handles for a noncreating, coherent Windows payload capture.

    Denying write/delete sharing also excludes an earlier updater which knows
    nothing about native-control. This does not attest process/store quiescence.
    POSIX qualification requires the existing installation control instead.
    """
    if os.name != "nt":
        raise NativeControlError()
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.CreateFileW.argtypes = (
        wintypes.LPCWSTR,
        wintypes.DWORD,
        wintypes.DWORD,
        ctypes.c_void_p,
        wintypes.DWORD,
        wintypes.DWORD,
        wintypes.HANDLE,
    )
    kernel.CreateFileW.restype = wintypes.HANDLE
    kernel.CloseHandle.argtypes = (wintypes.HANDLE,)
    kernel.CloseHandle.restype = wintypes.BOOL
    with ExitStack() as handles:

        def retain(relative: str) -> None:
            path = root / safe_path(relative)
            handle = kernel.CreateFileW(str(path), 0x80000000, 1, None, 3, 0x80, None)
            if handle == ctypes.c_void_p(-1).value:
                raise NativeControlError()
            handles.callback(kernel.CloseHandle, handle)

        retain(MANIFEST)
        manifest = parse_manifest(_read_regular(root, MANIFEST, MAX_MANIFEST))
        for row in manifest["files"]:
            retain(row["relative_path"])
        yield


def _receipt_handle(path: Path, access: int, flags: int) -> tuple[Any, Any]:
    """Open an exact Windows receipt object without delete sharing."""
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.CreateFileW.argtypes = (
        wintypes.LPCWSTR,
        wintypes.DWORD,
        wintypes.DWORD,
        ctypes.c_void_p,
        wintypes.DWORD,
        wintypes.DWORD,
        wintypes.HANDLE,
    )
    kernel.CreateFileW.restype = wintypes.HANDLE
    kernel.CloseHandle.argtypes = (wintypes.HANDLE,)
    kernel.CloseHandle.restype = wintypes.BOOL
    handle = kernel.CreateFileW(str(path), access, 3, None, 3, flags, None)
    if handle == wintypes.HANDLE(-1).value:
        raise ctypes.WinError(ctypes.get_last_error())
    return kernel, handle


def _receipt_stat(handle: Any) -> os.stat_result:
    """Use Python's dev/inode format for the opened Windows identity."""
    import msvcrt

    kernel = _kernel()
    duplicate = wintypes.HANDLE()
    current = kernel.GetCurrentProcess()
    if not kernel.DuplicateHandle(
        current, handle, current, ctypes.byref(duplicate), 0, False, 2
    ):
        raise ctypes.WinError(ctypes.get_last_error())
    value = duplicate.value
    if value is None:
        raise OSError("identity_handle_unavailable")
    try:
        fd = msvcrt.open_osfhandle(value, os.O_RDONLY | os.O_BINARY | os.O_NOINHERIT)
    except BaseException:
        kernel.CloseHandle(value)
        raise
    try:
        return os.fstat(fd)
    finally:
        os.close(fd)


@contextmanager
def _receipt_parent(path: Path) -> Iterator[int | None]:
    """Pin every ancestor; never traverse a directory link or reparse point."""
    with ExitStack() as held:
        descriptor = None
        for parent in reversed(path.parents):
            if os.name == "nt":
                kernel, handle = _receipt_handle(parent, 0x81, 0x02200000)
                held.callback(kernel.CloseHandle, handle)
                info = _receipt_stat(handle)
            else:
                if not hasattr(os, "O_DIRECTORY") or not hasattr(os, "O_NOFOLLOW"):
                    raise OSError("safe_directory_operations_unavailable")
                descriptor = os.open(
                    parent if descriptor is None else parent.name,
                    os.O_RDONLY | os.O_DIRECTORY | getattr(os, "O_NOFOLLOW"),
                    dir_fd=descriptor,
                )
                held.callback(os.close, descriptor)
                info = os.fstat(descriptor)
            if (
                not stat.S_ISDIR(info.st_mode)
                or getattr(info, "st_file_attributes", 0) & 0x400
            ):
                raise OSError("unsafe_directory")
        yield descriptor


def _receipt_dispose(
    path: Path, identity: tuple[int, int], descriptor: int | None
) -> str | None:
    """Remove only this new single-link receipt stage, by handle on Windows."""
    try:
        if os.name == "nt":
            kernel, handle = _receipt_handle(path, 0x10080, 0x02200000)
            try:
                info = _receipt_stat(handle)
                if (info.st_dev, info.st_ino) != identity:
                    return "identity_changed:None"
                if (
                    not stat.S_ISREG(info.st_mode)
                    or info.st_nlink != 1
                    or getattr(info, "st_file_attributes", 0) & 0x400
                ):
                    return "unsafe_path:None"
                kernel.SetFileInformationByHandle.argtypes = (
                    wintypes.HANDLE,
                    ctypes.c_int,
                    ctypes.c_void_p,
                    wintypes.DWORD,
                )
                kernel.SetFileInformationByHandle.restype = wintypes.BOOL
                disposition = wintypes.BOOL(True)
                if not kernel.SetFileInformationByHandle(
                    handle, 4, ctypes.byref(disposition), ctypes.sizeof(disposition)
                ):
                    raise ctypes.WinError(ctypes.get_last_error())
            finally:
                kernel.CloseHandle(handle)
        else:
            # As with Core staging, POSIX requires a producer-owned namespace.
            info = os.stat(path.name, dir_fd=descriptor, follow_symlinks=False)
            if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
                return "unsafe_path:None"
            if (info.st_dev, info.st_ino) != identity:
                return "identity_changed:None"
            os.unlink(path.name, dir_fd=descriptor)
    except FileNotFoundError:
        return None
    except OSError as error:
        return f"cleanup_pending:{getattr(error, 'winerror', None) or error.errno or 0}"
    return None


@contextmanager
def receipt_staging(destination: Path) -> Iterator[Path]:
    """Stage standalone failure receipts without importing or activating Core.

    Serialization and fsync policy belong to the two native receipt writers.
    This seam performs no manifest discovery, admission, adoption or recovery.
    """
    path = Path(destination).absolute()
    resource_id = uuid4().hex
    path = path.with_name(f".{path.name}.{resource_id}.tmp")
    with _receipt_parent(path) as descriptor:
        fd = os.open(
            path if descriptor is None else path.name,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0),
            0o666,
            dir_fd=descriptor,
        )
        try:
            info = os.fstat(fd)
            identity = info.st_dev, info.st_ino
        finally:
            os.close(fd)
        primary: BaseException | None = None
        try:
            yield path
        except BaseException as error:
            primary = error
            raise
        finally:
            result = _receipt_dispose(path, identity, descriptor)
            if result is not None:
                diagnostic = f"temporary_cleanup:{resource_id}:{result}"
                if primary is not None:
                    primary.add_note(diagnostic)
                else:
                    raise OSError(diagnostic)


def _read(path: Path, limit: int = 1024 * 1024) -> dict[str, Any]:
    raw = _read_regular(path.parent, path.name, limit)
    value = json.loads(raw, object_pairs_hook=_pairs, parse_constant=_no_number)
    if not isinstance(value, dict):
        raise NativeControlError()
    return value


def _atomic(path: Path, value: dict[str, Any] | str) -> None:
    """Same-directory, fsynced replacement; caller owns permanent ingress gate."""
    raw = value.encode("ascii") if isinstance(value, str) else canonical_json(value)
    temporary = path.with_name("." + path.name + "." + uuid4().hex)
    try:
        with temporary.open("xb") as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
        if os.name != "nt":
            fd = os.open(path.parent, os.O_RDONLY)
            try:
                os.fsync(fd)
            finally:
                os.close(fd)
    finally:
        temporary.unlink(missing_ok=True)


@dataclass(frozen=True)
class ManagedSelection:
    """Exact owner/routing/instance/target facts resolved under existing gates.

    The host resolver must read actual deployment/configuration facts; a request
    payload must never supply this object as an assertion of safety.
    """

    project: str
    workplace: str
    owner: str
    runtime_instance: str
    routing_revision: str
    targets: tuple[tuple[str, str, str, str], ...]
    _device_config_path: str = field(default="", compare=False, repr=False)

    def document(self) -> dict[str, Any]:
        return {
            "project": self.project,
            "workplace": self.workplace,
            "owner": self.owner,
            "runtime_instance": self.runtime_instance,
            "routing_revision": self.routing_revision,
            "targets": [list(row) for row in self.targets],
        }


@dataclass
class _LeaseLife:
    pid: int
    thread: int


def _bootstrap_control(
    root: Path, archive: str, guard: Path, epoch: Path
) -> NativeControl | None:
    """Retain an existing cooperating lease; no migration authority is derived."""
    if guard.exists() != epoch.exists():
        raise NativeControlError()
    if not guard.exists():
        return None
    accepted = _read_regular(epoch.parent, epoch.name, 256).decode("ascii")
    return NativeControl(guard, epoch, accepted)


def _native_life_held(control: NativeControl | None) -> bool:
    life = _OPERATION_LIFETIME.get()
    return (
        control is not None
        and _CONTROL_LEASE.get() is control
        and life is not None
        and life.active
        and life.pid == os.getpid()
        and life.thread_id == threading.get_ident()
    )


def _exclusive_lease_identity(control: NativeControl) -> dict[str, Any]:
    """Bind a live exclusive owner to its actually locked physical object.

    This is not publication, deployment or domain readiness authority. Shared
    operation leases cannot authorize controller mutation. A replaced guard or
    epoch cannot silently become the lock namespace of an existing cohort.
    """
    life = next(
        (
            life
            for owner, life in reversed(_EXCLUSIVE_LIFETIMES.get())
            if owner is control
        ),
        None,
    )
    if (
        life is None
        or not life.active
        or life.pid != os.getpid()
        or life.thread_id != threading.get_ident()
        or not life.exclusive
        or life.guard_fd is None
    ):
        raise NativeControlError()
    held = os.fstat(life.guard_fd)
    current = control.guard.lstat()
    if (
        (held.st_dev, held.st_ino) != life.guard_identity
        or (current.st_dev, current.st_ino) != life.guard_identity
        or not stat.S_ISREG(held.st_mode)
        or not stat.S_ISREG(current.st_mode)
        or held.st_nlink != 1
        or current.st_nlink != 1
        or getattr(current, "st_file_attributes", 0) & 0x400
    ):
        raise NativeControlError()
    with control.epoch_path.open("rb") as epoch:
        raw = epoch.read(257)
        epoch_info = os.fstat(epoch.fileno())
    epoch_current = control.epoch_path.lstat()
    if (
        not stat.S_ISREG(epoch_info.st_mode)
        or not stat.S_ISREG(epoch_current.st_mode)
        or epoch_info.st_nlink != 1
        or epoch_current.st_nlink != 1
        or (epoch_info.st_dev, epoch_info.st_ino)
        != (epoch_current.st_dev, epoch_current.st_ino)
        or getattr(epoch_current, "st_file_attributes", 0) & 0x400
        or raw != control.accepted_epoch.encode("ascii")
    ):
        raise NativeControlError()
    return {
        "guard_path": str(control.guard.absolute()),
        "guard_identity": [held.st_dev, held.st_ino],
        "epoch_path": str(control.epoch_path.absolute()),
        "epoch_identity": [epoch_info.st_dev, epoch_info.st_ino],
        "accepted_epoch": control.accepted_epoch,
    }


def _update_now() -> str:
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _update_target(root: Path, relative: str) -> Path:
    target = root / safe_path(relative)
    for part in (target, *target.parents):
        if part == root:
            break
        if part.exists() or part.is_symlink():
            info = part.lstat()
            if (
                stat.S_ISLNK(info.st_mode)
                or getattr(info, "st_file_attributes", 0) & 0x400
            ):
                raise NativeControlError()
    if not target.resolve().is_relative_to(root.resolve()):
        raise NativeControlError()
    return target


def _freeze_update_archive(raw: bytes, plan: Mapping[str, Any]) -> Build:
    """Freeze qualified archive bytes once; current installed files grant no pins."""
    import zipfile

    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        if len(archive.namelist()) != len(set(archive.namelist())):
            raise NativeControlError()
        manifest = archive.read(MANIFEST)
        parsed = parse_manifest(manifest)
        if parsed != plan["new_manifest"]:
            raise NativeControlError()
        payload = {
            row["relative_path"]: archive.read(row["relative_path"])
            for row in parsed["files"]
        }
    leaf = payload[LEAF]
    seal = leaf_seal(leaf)
    if seal is None or digest(projection(manifest)) != seal[1]:
        raise NativeControlError()
    for row in parsed["files"]:
        content = payload[row["relative_path"]]
        if len(content) != row["size"] or digest(content) != row["sha256"]:
            raise NativeControlError()
    if payload[INVENTORY] != inventory_bytes(payload):
        raise NativeControlError()
    return Build(MappingProxyType(payload), manifest, seal[1])
