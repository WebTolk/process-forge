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
from dataclasses import dataclass, field, replace
from pathlib import Path
from types import FrameType, MappingProxyType
from typing import Any
from uuid import uuid4

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
    **options: Any,
) -> subprocess.Popen[bytes]:
    """Assign a suspended child to its retained Job before its first instruction.

    A duplicate Job handle is inherited by exactly the launched root. Therefore
    abrupt controller death cannot leave a wrapper without a containment fence.
    Child death closes that handle; last-handle close kills remaining members.
    """
    if os.name != "nt":
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
) -> OwnedJob | None:
    """Reopen only exact persisted attempt ownership; PID reuse cannot signal it.

    None means the authenticated non-breakaway Job no longer exists. Any access
    denial or identity mismatch raises; arbitrary legacy PID facts grant nothing.
    """
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
class NativeImage:
    """Immutable accepted source/resources, including direct spec loaders.

    Capture is noncreating. It never derives expected pins from current source
    files. Only explicitly accepted payload paths can be loaded from this root.
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
            if report_output:
                target = image.root.joinpath(*report_parts)
                # Only these mutable outputs may bypass the accepted byte image.
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
                    or opener is not None
                    or not closefd
                ):
                    raise NativeControlError()
            if relative is None or relative.startswith("runtime/") or report_output:
                return original_open(
                    file, mode, buffering, encoding, errors, newline, closefd, opener
                )
            if mode not in {"r", "rt", "rb"} or opener is not None or not closefd:
                raise NativeControlError()
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
                with self.epoch_path.open("rb") as epoch:
                    raw = epoch.read(257)
                if (
                    len(raw) > 256
                    or raw.decode("ascii") != self.accepted_epoch
                    or time.monotonic() >= stop
                ):
                    raise NativeControlError()
                if not exclusive:
                    _validate_shared_head(self)
                token = _CONTROL_LEASE.set(self)
                life = _OperationLifetime(os.getpid(), threading.get_ident())
                life_token = _OPERATION_LIFETIME.set(life)
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
                if life_token is not None:
                    _OPERATION_LIFETIME.reset(life_token)
                if token is not None:
                    _CONTROL_LEASE.reset(token)
                if locked:
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


_OPERATION_LIFETIME: ContextVar[_OperationLifetime | None] = ContextVar(
    "pf_native_operation_lifetime", default=None
)


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
        raw = stream.read(limit + 1)
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
            raw = stream.read(limit + 1)
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
        "tools/prepared_executor.py",
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

    def storage_safety(self, context: Any) -> tuple[str, str, tuple[str, ...]]:
        return _managed_storage_safety(self, context)

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
    if seal is None:
        return NativeEntry(root, None, None, None)
    for path in (root, *root.parents):
        info = path.lstat()
        if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & 0x400:
            raise NativeControlError()
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


_REPLACEMENT_TARGET: ContextVar[NativeEntry | None] = ContextVar(
    "pf_replacement_target", default=None
)
_UPDATE_PLAN_ENTRY: ContextVar[NativeEntry | _MaintenanceTarget | None] = ContextVar(
    "pf_update_plan_entry", default=None
)


def _replacement_target(entry: NativeEntry) -> AbstractContextManager[None]:
    """Bind an already qualified target for management Core's existing apply.

    The native host supplies its retained adoption/attach entry, never a root
    discovered from CLI arguments. This scope creates no authority or lease;
    replacement revalidates the exact entry under target ingress/exclusive.
    """

    class Target(AbstractContextManager[None]):
        def __enter__(self) -> None:
            if (
                _REPLACEMENT_TARGET.get() is not None
                or _CONTROL_LEASE.get() is not None
            ):
                raise NativeControlError()
            self.token = _REPLACEMENT_TARGET.set(entry)

        def __exit__(self, *_exception: Any) -> None:
            # Core's frozen errors must not be thrown through a generator scope.
            _REPLACEMENT_TARGET.reset(self.token)

    return Target()


@dataclass(frozen=True)
class _MaintenanceTarget:
    """Authenticated target data; never an executable entry or image."""

    root: Path
    control: NativeControl
    generation: str
    manifest: bytes
    maintenance: Mapping[str, str]
    selection: Mapping[str, Any]
    owned_paths: frozenset[str]


def _maintenance_record(value: Any) -> dict[str, str]:
    if (
        not isinstance(value, dict)
        or set(value) != {"manifest_sha256", "device_config_path"}
        or not isinstance(value["manifest_sha256"], str)
        or not HEX.fullmatch(value["manifest_sha256"])
        or not isinstance(value["device_config_path"], str)
        or not value["device_config_path"]
        or not Path(value["device_config_path"]).is_absolute()
        or str(Path(value["device_config_path"]).resolve())
        != value["device_config_path"]
    ):
        raise NativeControlError()
    return value


def _accepted_maintenance(state: dict[str, Any]) -> dict[str, str] | None:
    record = (
        state["successors"][-1]
        if state["successors"]
        else state["retirement"]["baseline"]
    )
    return (
        _maintenance_record(record["maintenance"]) if "maintenance" in record else None
    )


def _issued_maintenance(
    publication: Publication, selection: ManagedSelection
) -> dict[str, str] | None:
    # Old private/synthetic issuers remain old-form, without repair authority.
    # Real host selections carry their actual source locator, never a digest-derived guess.
    if not selection._device_config_path:
        return None
    from processforge_core.composition import _update_selection

    with _update_selection(
        selection.document(), Path(selection._device_config_path)
    ) as (actual, _):
        return _maintenance_record(
            {
                "manifest_sha256": publication.manifest_sha256,
                "device_config_path": actual._device_config_path,
            }
        )


def _maintenance_manifest(
    root: Path, state: dict[str, Any], maintenance: Mapping[str, str]
) -> bytes:
    raw = _read_regular(root, MANIFEST, MAX_MANIFEST)
    if (
        digest(raw) != maintenance["manifest_sha256"]
        or digest(projection(raw)) != state["archive"]
    ):
        raise NativeControlError()
    rows = {row["relative_path"]: row for row in parse_manifest(raw)["files"]}
    inventory = "".join(
        f"{row['sha256']}  {path}\n"
        for path, row in sorted(rows.items())
        if path != INVENTORY
    ).encode("utf-8")
    if (
        len(inventory) != rows[INVENTORY]["size"]
        or digest(inventory) != rows[INVENTORY]["sha256"]
    ):
        raise NativeControlError()
    return raw


def _update_entry(core_root: Path) -> NativeEntry | _MaintenanceTarget:
    execution = current_entry()
    if execution is None or execution.publication is None or execution.image is None:
        raise NativeControlError()
    root = core_root.absolute()
    for path in (root, *root.parents):
        info = path.lstat()
        if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & 0x400:
            raise NativeControlError()
    root = root.resolve(strict=True)
    entry = _REPLACEMENT_TARGET.get()
    if entry is not None:
        if entry.root != root:
            raise NativeControlError()
        return entry
    if execution.root == root:
        return execution
    if execution.root in root.parents or root in execution.root.parents:
        raise NativeControlError()
    # Noncreating exact-root lookup: no scan, enrollment or executable target capture.
    producer = ManagedEnrollmentProducer(root, b"")
    try:
        state = producer._state()
        if state["phase"] != "bound":
            raise NativeControlError()
        control = producer._control(state)
        maintenance = _accepted_maintenance(state)
        if maintenance is None:
            raise NativeControlError()
        raw = _maintenance_manifest(root, state, maintenance)
        return _MaintenanceTarget(
            root,
            control,
            state["adoption"],
            raw,
            MappingProxyType(dict(maintenance)),
            MappingProxyType(dict(state["selection"])),
            frozenset(row["relative_path"] for row in parse_manifest(raw)["files"]),
        )
    except (
        OSError,
        ValueError,
        KeyError,
        TypeError,
    ):
        raise NativeControlError() from None


def _update_plan_path(path: Path) -> tuple[NativeEntry | _MaintenanceTarget, str]:
    """Physical target data only during the once-only exclusive planner."""
    entry = _UPDATE_PLAN_ENTRY.get()
    if entry is None or not _native_life_held(entry.control):
        raise NativeControlError()
    try:
        relative = path.absolute().relative_to(entry.root).as_posix()
    except ValueError:
        raise NativeControlError() from None
    owned = (
        entry.owned_paths
        if isinstance(entry, _MaintenanceTarget)
        else (entry.publication.payload if entry.publication is not None else {})
    )
    if relative != MANIFEST and relative not in owned:
        raise NativeControlError()
    return entry, safe_path(relative)


def _update_selection_inputs() -> tuple[dict[str, Any], str | None]:
    entry = _UPDATE_PLAN_ENTRY.get()
    if entry is None or not _native_life_held(entry.control):
        raise NativeControlError()
    producer = ManagedEnrollmentProducer(entry.root, b"")
    state = producer._state()
    maintenance = _accepted_maintenance(state)
    return state["selection"], maintenance[
        "device_config_path"
    ] if maintenance else None


def _read_update_plan_file(path: Path) -> bytes:
    entry, relative = _update_plan_path(path)
    if relative != MANIFEST:
        raise NativeControlError()
    return _read_regular(entry.root, relative, MAX_MANIFEST)


def _sha256_update_plan_file(path: Path) -> str:
    entry, relative = _update_plan_path(path)
    target = _update_target(entry.root, relative)
    info = target.lstat()
    if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
        raise NativeControlError()
    # Local preimages need not have the old release's size. Stream physical
    # bytes without the publication capture limit or the Core digest cache.
    result = hashlib.sha256()
    with _PHYSICAL_OPEN(target, "rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            result.update(chunk)
    return result.hexdigest()


def supports_owned_execution() -> bool:
    """Probe the actual retained whole-tree backend, independently of SQLite.

    Explicit initialization probes real suspended creation/Job attachment. It creates no guard,
    database, UUID metadata or maintenance evidence on an unsupported host.
    """
    if os.name != "nt" or _ENTRY is None or _ENTRY.publication is None:
        return False
    try:
        process = spawn_owned(
            [sys.executable, "-B", "-c", "pass"],
            env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        job = getattr(process, "native_job")
        try:
            return process.wait(timeout=5) == 0 and job.active() == 0
        finally:
            if process.poll() is None:
                job.stop(deadline=time.monotonic() + 5)
                process.wait(timeout=5)
            job.close()
    except (
        OSError,
        AttributeError,
        ValueError,
        subprocess.SubprocessError,
    ):
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
    active: bool = True

    def live(self) -> bool:
        return (
            self.active
            and self.pid == os.getpid()
            and self.thread == threading.get_ident()
        )


@dataclass(frozen=True)
class _HeldProof:
    producer: ManagedEnrollmentProducer
    entry: NativeEntry
    selection: ManagedSelection
    resolver: Callable[[], ManagedSelection]
    admission_held: Callable[[], bool]
    generation: str
    state: dict[str, Any]
    life: _LeaseLife


_HELD: ContextVar[_HeldProof | None] = ContextVar(
    "managed_enrollment_held", default=None
)
_LEGACY_HELD: ContextVar[tuple[tuple[LegacyManagedBoundary, _LeaseLife], ...]] = (
    ContextVar("managed_original_gate_held", default=())
)


class LegacyManagedBoundary:
    """Version-independent facade of the EXISTING trusted managed launcher.

    Existing launcher owns the permanent ingress OS gate and accepted archive
    bytes since installation, plus every Job created under it. This object must
    be the live manager, not a reconstructed caller list. It creates no new disk
    registry/guard/epoch and cannot manufacture historical completeness.
    Archive bytes come from qualified archive/installation ingress, not disk
    self-hashes. No domain work executes in the launcher itself.
    """

    INGRESS = frozenset({"cli", "runtime", "mcp", "hook", "worker", "updater"})

    def __init__(
        self,
        root: Path,
        *,
        existing_gate: NativeControl,
        accepted_archive: Mapping[str, bytes],
    ) -> None:
        if not accepted_archive or os.name != "nt":
            raise NativeControlError()
        self.root = root.resolve(strict=True)
        self.gate = existing_gate
        self.archive = MappingProxyType(dict(accepted_archive))
        self.archive_pin = digest(
            canonical_json(
                {path: digest(raw) for path, raw in sorted(self.archive.items())}
            )
        )
        self.owners: dict[str, list[subprocess.Popen[bytes]]] = {
            ingress: [] for ingress in self.INGRESS
        }
        self.anchor = OwnedJob.create()
        self.poisoned = False
        self.installed_verified = False
        self.producer: ManagedEnrollmentProducer | None = None
        with self.held():
            # This verifies initial installed/archive identity at the trusted
            # manager's existing deployment boundary, before any managed starts.
            for path, expected in self.archive.items():
                if _read_regular(self.root, safe_path(path), len(expected)) != expected:
                    raise NativeControlError()
            self.installed_verified = True

    @contextmanager
    def held(self) -> Iterator[None]:
        if any(owner is self and life.live() for owner, life in _LEGACY_HELD.get()):
            yield
            return
        with self.gate.exclusive():
            token = _CONTROL_LEASE.set(None)
            life = _LeaseLife(os.getpid(), threading.get_ident())
            original = _LEGACY_HELD.set((*_LEGACY_HELD.get(), (self, life)))
            try:
                yield
            finally:
                life.active = False
                _LEGACY_HELD.reset(original)
                _CONTROL_LEASE.reset(token)

    @contextmanager
    def replacement(self, *, target_leaf: bytes) -> Iterator[LegacyManagedBoundary]:
        """Pre-native updater boundary, BEFORE first old-install overwrite.

        Existing updater copies accepted payload while this context remains held;
        then from_legacy_manager revalidates/adopts the new entry before release.
        No old domain/lazy writes may occur after overwrite. Old guard/epoch are
        not required. Interrupted replacement remains existing updater recovery.
        """
        with self.held():
            seal = leaf_seal(target_leaf)
            if seal is None:
                raise NativeControlError()
            closure, _ = self.facts()
            if closure != "proven" or self.producer is not None:
                raise NativeControlError()
            for path, expected in self.archive.items():
                if _read_regular(self.root, safe_path(path), len(expected)) != expected:
                    raise NativeControlError()
            directory = self.root / "runtime/managed-ingress"
            directory.mkdir(parents=True, exist_ok=True)
            fence = {"legacy_archive": self.archive_pin, "destination": seal[1]}
            fence_path = directory / "legacy-replacement.json"
            if fence_path.exists() and _read(fence_path, 4096) != fence:
                raise NativeControlError()
            _atomic(fence_path, fence)
            yield self
            if self.producer is None or self.producer._state()["phase"] != "bound":
                raise NativeControlError()

    def launch(
        self, argv: list[str], *, ingress: str, **options: Any
    ) -> subprocess.Popen[bytes]:
        """Existing controlled ingress covers capture, launch gap and child tree.

        No new reservation files. The gate spans first payload read through
        retained native owner publication. Manager death invalidates baseline;
        receipts/empty lists cannot be used to reconstruct this authority.
        """
        if ingress not in self.INGRESS:
            raise NativeControlError()
        with self.held():
            if (self.root / "runtime/managed-ingress/legacy-replacement.json").exists():
                raise NativeControlError()
            if self.producer is not None:
                # Bound/pending enrollment permanently refuses old starts.
                return self.producer.launch_legacy(
                    argv, ingress=ingress, identity={}, **options
                )
            if self.poisoned or not self.installed_verified:
                raise NativeControlError()
            try:
                process = spawn_owned(argv, **options)
                self.owners[ingress].append(process)
                return process
            except BaseException:
                self.poisoned = True
                raise

    def facts(self) -> tuple[str, list[dict[str, Any]]]:
        """Caller holds actual existing launch gate; enumerate ALL manager owners."""
        if (
            not self.installed_verified
            or self.poisoned
            or not self.anchor.handle
            or self.anchor.active() != 0
            or set(self.owners) != self.INGRESS
        ):
            return "unknown", []
        records = []
        active = False
        for ingress in sorted(self.owners):
            for process in self.owners[ingress]:
                job = getattr(process, "native_job", None)
                facts = getattr(process, "native_facts", None)
                if job is None or not job.handle or not isinstance(facts, dict):
                    return "unknown", []
                active |= job.active() != 0
                records.append({"ingress": ingress, "facts": facts})
        return "active" if active else "proven", records


class ManagedEnrollmentProducer:
    """Produce proof from complete managed ingress and native tree observations.

    Trust root: qualified managed launcher + interpreter and accepted archive.
    All CLI, Runtime/MCP, hooks, workers, updater and attempt trees of the declared
    installation must enter this launcher BEFORE capturing any payload bytes.
    A durable reservation precedes spawn; spawn_owned publishes Job facts before
    resuming user code. Crash windows remain unknown. No terminal/PID/TTL inference.
    """

    def __init__(self, root: Path, trusted_leaf: bytes) -> None:
        self.root = root.resolve(strict=True)
        self.trusted_leaf = trusted_leaf
        self.directory = self.root / "runtime/managed-ingress"
        self.state_path = self.directory / "baseline.json"
        self.gate = NativeControl(
            self.directory / "ingress.guard", self.directory / "protocol", "managed-v1"
        )
        self._jobs: list[Any] = []
        self.legacy_boundary: LegacyManagedBoundary | None = None

    @classmethod
    def from_cold_provider(
        cls, authority: Any, entry: NativeEntry, *, selection: ManagedSelection
    ) -> tuple[ManagedEnrollmentProducer, NativeEntry]:
        """Consume real held provider, not a cold bool or fake original manager.

        Cold controller stays held through pending, guard, epoch, bound and head.
        Exact pending resume requires newly validated live cold authority. After
        durable bound the inherited independent operation/short-lease protocol
        works without the controller. Publication/full chain checks are outside
        bounded admission. No target migration executes in this constructor.
        """
        from pf_cold_controller import Authority

        _cold_require(isinstance(authority, Authority))
        authority.verify()
        controller = authority.controller
        cold = controller.state()
        _cold_require(cold["phase"] in {"installed", "bound"})
        _cold_require(cold["selection"] == selection.document())
        _cold_require(entry.root in controller.fence.roots)
        if entry.publication is None:
            raise NativeControlError()
        _cold_require(
            cold["installed"]
            == {
                "root": str(entry.root),
                "archive": cold["archive"],
                "manifest": entry.publication.manifest_sha256,
                "publication": entry.publication.projection_sha256,
                "leaf": digest(entry.publication.payload[LEAF]),
            }
        )
        _cold_require(_CONTROL_LEASE.get() is controller.control)
        # The external maintenance gate is a different lock namespace. Avoid
        # erasing a live installation lease or shared->exclusive upgrade.
        _cold_require(
            controller.control.guard
            != entry.root / "runtime/native-control/installation.guard"
        )
        producer = cls(entry.root, entry.publication.payload[LEAF])
        # NativeControl uses one contextvar for distinct locks; caller retains
        # real external OS lock and Authority.life while internal scopes run.
        token = _CONTROL_LEASE.set(None)
        try:
            producer.directory.mkdir(parents=True, exist_ok=True)
            guard, protocol = (
                producer.directory / "ingress.guard",
                producer.directory / "protocol",
            )
            if not guard.exists():
                with guard.open("xb") as stream:
                    stream.write(b"0")
                    stream.flush()
                    os.fsync(stream.fileno())
            if not protocol.exists():
                _atomic(protocol, "managed-v1")
            with producer._ingress():
                with _publication_read_exclusion(entry.root):
                    publication = producer._publication(entry)
                    control_directory = entry.root / "runtime/native-control"
                    control_directory.mkdir(exist_ok=True)
                    native_guard, epoch = (
                        control_directory / "installation.guard",
                        control_directory / "epoch",
                    )
                    if not native_guard.exists():
                        with native_guard.open("xb") as stream:
                            stream.write(b"0")
                            stream.flush()
                            os.fsync(stream.fileno())
                    record = {
                        key: cold[key]
                        for key in (
                            "transaction",
                            "archive",
                            "policy",
                            "namespace",
                            "retirement",
                        )
                    }
                    # No installation paths/ACLs in the bounded head. Full
                    # private fence metadata remains external recovery evidence.
                    record["fence_commitment"] = cold["retirement_fence"]
                    baseline = {
                        "origin": "cold-v1",
                        "installation": cold["transaction"],
                        "archive": publication.projection_sha256,
                        "selection": selection.document(),
                        "cold": record,
                    }
                    maintenance = _issued_maintenance(publication, selection)
                    if maintenance is not None:
                        baseline["maintenance"] = maintenance
                    generation = "sha256:" + digest(canonical_json(baseline))
                    state = {
                        "schema": 1,
                        "origin": "cold-v1",
                        "installation": cold["transaction"],
                        "archive": publication.projection_sha256,
                        "selection": selection.document(),
                        "phase": "pending",
                        "adoption": generation,
                        "replacement": None,
                        "retirement": {
                            "binding": producer._binding(),
                            "baseline": baseline,
                            "generation": generation,
                        },
                        "successors": [],
                    }
                    if producer.state_path.exists():
                        existing = producer._state()
                        _cold_require(existing["phase"] in {"pending", "bound"})
                        _cold_require(dict(existing, phase="pending") == state)
                    else:
                        _atomic(producer.state_path, state)
                    expected = producer._epoch(state)
                    if epoch.exists():
                        _cold_require(
                            _read_regular(control_directory, "epoch", 256)
                            == expected.encode("ascii")
                        )
                    else:
                        _atomic(epoch, expected)
                    control = NativeControl(native_guard, epoch, expected)
                    with control.exclusive():
                        producer._durable(state)
                        _cold_require(
                            controller._authority is authority and authority.active
                        )
                        # New native files inherit the maintenance-only fence.
                        # This is an actual effective-access check, not a receipt.
                        controller.fence.verify()
                        state["phase"] = "bound"
                        _atomic(producer.state_path, state)
                        producer._publish_head(state)
                    adopted = replace(entry, control=producer._control(state))
        finally:
            _CONTROL_LEASE.reset(token)
        # Native additions changed gate inventory. Refresh only under the live
        # controller, while all target objects still deny normal tokens.
        current = controller.state()
        current["fence"] = controller.fence.verify()
        from pf_cold_controller import atomic

        atomic(controller.directory / "cold.json", current)
        if adopted.control is None:
            raise NativeControlError()
        controller.bound(authority, adopted.control.accepted_epoch)
        return producer, adopted

    @classmethod
    def from_legacy_manager(
        cls,
        boundary: LegacyManagedBoundary,
        entry: NativeEntry,
        *,
        selection: ManagedSelection,
        checkpoint: Callable[[str], None] = lambda _: None,
    ) -> tuple[ManagedEnrollmentProducer, NativeEntry]:
        """Adopt REAL older managed owners with no new reservation records.

        Existing supervisor/gate remains held through closure, current accepted
        image revalidation, durable import and native adoption. The old manager
        must call this handoff itself; no user-supplied owner list or proof flag.
        Interrupted import keeps exact old baseline and blocks both ingress paths.
        """
        producer = cls(
            boundary.root,
            entry.publication.payload[LEAF] if entry.publication else b"",
        )
        producer.legacy_boundary = boundary
        with boundary.held():
            closure, owners = boundary.facts()
            if closure != "proven":
                raise NativeControlError()
            # Authenticated old archive facts were captured by the original
            # manager; accepted current publication may now be the new release.
            with _publication_read_exclusion(boundary.root):
                publication = producer._publication(entry)
                fence = producer.directory / "legacy-replacement.json"
                if fence.exists() and _read(fence, 4096) != {
                    "legacy_archive": boundary.archive_pin,
                    "destination": publication.projection_sha256,
                }:
                    raise NativeControlError()
                producer.directory.mkdir(parents=True, exist_ok=True)
                guard = producer.directory / "ingress.guard"
                protocol = producer.directory / "protocol"
                if producer.state_path.exists():
                    state = producer._state()
                    recorded = [
                        _read(producer.directory / (row["slot"] + ".json"))
                        for row in state["launches"]
                    ]
                    if state.get("legacy_archive") != boundary.archive_pin or sorted(
                        canonical_json(row) for row in recorded
                    ) != sorted(canonical_json(row["facts"]) for row in owners):
                        raise NativeControlError()
                else:
                    # This is not an empty-registry proof: original manager's
                    # entire retained owner set was queried under its real gate.
                    guard.touch(exist_ok=True)
                    protocol.write_text("managed-v1", encoding="ascii")
                    records = []
                    for row in owners:
                        slot = uuid4().hex
                        facts = row["facts"]
                        _atomic(producer.directory / (slot + ".json"), facts)
                        records.append({"slot": slot, "identity": facts["identity"]})
                    state = {
                        "schema": 1,
                        "installation": uuid4().hex,
                        "archive": publication.projection_sha256,
                        "selection": selection.document(),
                        "sentinel": boundary.anchor.name,
                        "launches": records,
                        "phase": "legacy",
                        "adoption": None,
                        "replacement": None,
                        "legacy_archive": boundary.archive_pin,
                    }
                    _atomic(producer.state_path, state)
                # Connect old ingress BEFORE pending. If exact native adoption
                # fails, both entry paths still serialize on producer ingress.
                boundary.producer = producer
            adopted = producer.enroll(entry, selection=selection, checkpoint=checkpoint)
        return producer, adopted

    @contextmanager
    def _ingress(self, deadline: float | None = None) -> Iterator[None]:
        # Reuse the real NativeControl OS lock. Its operation-local marker is
        # separate from the installation marker, so no shared->exclusive upgrade
        # or false nested ownership is introduced.
        with self.gate.exclusive(deadline=deadline):
            token = _CONTROL_LEASE.set(None)
            try:
                yield
            finally:
                _CONTROL_LEASE.reset(token)

    def _publish_head(self, state: dict[str, Any]) -> None:
        _atomic(
            self.directory / "adoption.json",
            {
                "installation": state["installation"],
                "archive": state["archive"],
                "generation": state["adoption"],
                "phase": state["phase"],
                "epoch": state["replacement"]["pending_epoch"]
                if state["phase"] == "updating"
                else self._epoch(state),
            },
        )

    @classmethod
    def begin_managed_installation(
        cls, root: Path, *, trusted_leaf: bytes, selection: ManagedSelection
    ) -> ManagedEnrollmentProducer:
        """Automatic trusted managed-install path, BEFORE its first legacy start.

        Never call for arbitrary existing/unmanaged copies. This is not a public
        setup flag or an operator receipt. A legacy manager already retaining all
        old owners needs a separate exact-handle handoff, not this initializer.
        """
        if os.name != "nt":
            raise NativeControlError()
        producer = cls(root, trusted_leaf)
        with _publication_read_exclusion(root):
            publication = accept_publication(root, trusted_leaf=trusted_leaf)
            if publication is None:
                raise NativeControlError()
            # Exclusive directory creation prevents two initializers and refuses
            # interrupted initialization. Never turn an empty registry into proof.
            producer.directory.mkdir(parents=True, exist_ok=False)
            (producer.directory / "ingress.guard").write_bytes(b"0")
            (producer.directory / "protocol").write_text("managed-v1", encoding="ascii")
            with producer._ingress():
                sentinel = OwnedJob.create()
                producer._jobs.append(sentinel)
                _atomic(
                    producer.state_path,
                    {
                        "schema": 1,
                        "installation": uuid4().hex,
                        "archive": publication.projection_sha256,
                        "selection": selection.document(),
                        "sentinel": sentinel.name,
                        "launches": [],
                        "phase": "legacy",
                        "adoption": None,
                        "replacement": None,
                    },
                )
        return producer

    def _state(self) -> dict[str, Any]:
        state = _read(self.state_path)
        if state.get("origin") != "cold-v1":
            return self._legacy_state()
        _cold_require(
            set(state)
            == {
                "schema",
                "installation",
                "archive",
                "selection",
                "phase",
                "adoption",
                "replacement",
                "retirement",
                "successors",
                "origin",
            }
        )
        _cold_require(type(state["schema"]) is int and state["schema"] == 1)
        _cold_require(state["phase"] in {"pending", "bound", "updating"})
        return state

    def _legacy_state(self) -> dict[str, Any]:
        state = _read(self.state_path)
        if (
            set(state) - {"legacy_archive", "retirement", "successors"}
            != {
                "schema",
                "installation",
                "archive",
                "selection",
                "sentinel",
                "launches",
                "phase",
                "adoption",
                "replacement",
            }
            or state["schema"] != 1
            or state["phase"] not in {"legacy", "pending", "bound", "updating"}
            or not isinstance(state["launches"], list)
            or not isinstance(state["installation"], str)
            or len(state["installation"]) != 32
        ):
            raise NativeControlError()
        return state

    def _publication(self, entry: NativeEntry | None = None) -> Publication:
        try:
            publication = accept_publication(self.root, trusted_leaf=self.trusted_leaf)
        except (
            OSError,
            ValueError,
        ):
            raise NativeControlError() from None
        if publication is None or (
            entry is not None
            and (entry.root != self.root or entry.publication != publication)
        ):
            raise NativeControlError()
        return publication

    def _replacement_authority(
        self, entry: NativeEntry | _MaintenanceTarget, state: dict[str, Any]
    ) -> None:
        """Validate retained old authority, not repairable executable payload.

        Called only under target ingress and installation exclusive. The old
        publication/image came from genuine earlier admission; physical target
        bytes are planner data and must never be captured or activated here.
        """
        if isinstance(entry, _MaintenanceTarget):
            target_control = entry.control
            self._durable(state)
            if (
                entry.root != self.root
                or entry.generation != state["adoption"]
                or dict(entry.selection) != state["selection"]
                or dict(entry.maintenance) != _accepted_maintenance(state)
                or target_control.guard
                != self.root / "runtime/native-control/installation.guard"
                or target_control.epoch_path
                != self.root / "runtime/native-control/epoch"
                or not _native_life_held(target_control)
                or target_control.accepted_epoch != self._epoch(state)
                or _maintenance_manifest(self.root, state, entry.maintenance)
                != entry.manifest
            ):
                raise NativeControlError()
            if _read(self.directory / "adoption.json", 4096) != {
                "installation": state["installation"],
                "archive": state["archive"],
                "generation": state["adoption"],
                "phase": "bound",
                "epoch": target_control.accepted_epoch,
            }:
                raise NativeControlError()
            return
        publication, image, control = entry.publication, entry.image, entry.control
        if publication is None or image is None or control is None:
            raise NativeControlError()
        seal = leaf_seal(self.trusted_leaf)
        if (
            entry.root != self.root
            or image.root != self.root
            or control.guard != self.root / "runtime/native-control/installation.guard"
            or control.epoch_path != self.root / "runtime/native-control/epoch"
            or not _native_life_held(control)
            or seal is None
            or publication.payload.get(LEAF) != self.trusted_leaf
            or publication.projection_sha256 != seal[1]
            or state["archive"] != seal[1]
            or digest(publication.manifest) != publication.manifest_sha256
            or digest(projection(publication.manifest)) != seal[1]
            or dict(image.files)
            != {**publication.payload, MANIFEST: publication.manifest}
            or _read_regular(self.root, MANIFEST, MAX_MANIFEST) != publication.manifest
        ):
            raise NativeControlError()
        # _durable binds selection to the retired baseline and validates the
        # full successor chain/binding. The retained epoch commits that chain.
        self._durable(state)
        if control.accepted_epoch != self._epoch(state):
            raise NativeControlError()
        head = _read(self.directory / "adoption.json", 4096)
        if head != {
            "installation": state["installation"],
            "archive": state["archive"],
            "generation": state["adoption"],
            "phase": "bound",
            "epoch": control.accepted_epoch,
        }:
            raise NativeControlError()

    def launch_legacy(
        self,
        argv: list[str],
        *,
        ingress: str,
        identity: Mapping[str, Any],
        **options: Any,
    ) -> subprocess.Popen[bytes]:
        """Managed owner starts, including already captured legacy code, use Job.

        One reservation belongs to one exact attempt. Persisted reservations are
        never discarded as stale and block adoption if no authenticated Job exists.
        """
        if ingress not in {"cli", "runtime", "mcp", "hook", "worker", "updater"}:
            raise NativeControlError()
        with self._ingress():
            state = self._state()
            if state["phase"] != "legacy":
                raise NativeControlError()
            publication = self._publication()
            if state["archive"] != publication.projection_sha256:
                raise NativeControlError()
            slot = uuid4().hex
            job_identity = {
                "installation": state["installation"],
                "ingress": ingress,
                "slot": slot,
                "attempt_identity": dict(identity),
            }
            state["launches"].append({"slot": slot, "identity": job_identity})
            _atomic(self.state_path, state)
            # This call writes receipt before first user instruction. If it fails,
            # keep reservation; interrupted launch is unknown until exact recovery.
            process = spawn_owned(
                argv,
                receipt_path=self.directory / (slot + ".json"),
                identity=job_identity,
                **options,
            )
            self._jobs.append(getattr(process, "native_job"))
            return process

    def _closure(self, state: dict[str, Any]) -> str:
        if state["phase"] in {"legacy", "pending"}:
            return self._legacy_closure(state)
        try:
            self._durable(state)
            return "proven"
        except (
            OSError,
            ValueError,
            KeyError,
            TypeError,
        ):
            return "unknown"

    def inspect(self) -> str:
        """Noncreating closure observation. This verdict alone is not a lease."""
        try:
            with self._ingress():
                return self._closure(self._state())
        except (
            OSError,
            ValueError,
            KeyError,
            TypeError,
        ):
            return "unknown"

    def enroll(
        self,
        entry: NativeEntry,
        *,
        selection: ManagedSelection,
        checkpoint: Callable[[str], None] = lambda _: None,
    ) -> NativeEntry:
        if _CONTROL_LEASE.get() is not None:
            raise NativeControlError()
        with self._ingress():
            state = self._state()
            with _publication_read_exclusion(self.root):
                publication = self._publication(entry)
                if (
                    state["archive"] != publication.projection_sha256
                    or state["selection"] != selection.document()
                    or state["phase"] == "updating"
                ):
                    raise NativeControlError()
                if state["phase"] == "bound":
                    self._durable(state)
                    control = self._control(state)
                    with control.exclusive():
                        self._publish_head(state)
                    return replace(entry, control=control)
                if self._legacy_closure(state) != "proven":
                    raise NativeControlError()
                baseline = {
                    key: state[key]
                    for key in (
                        "installation",
                        "archive",
                        "selection",
                        "sentinel",
                        "launches",
                    )
                }
                if "legacy_archive" in state:
                    baseline["legacy_archive"] = state["legacy_archive"]
                maintenance = _issued_maintenance(publication, selection)
                if maintenance is not None:
                    baseline["maintenance"] = maintenance
                # Exact old pending records keep their original committed shape.
                if state["phase"] == "pending" and "retirement" in state:
                    retained_baseline = state["retirement"]["baseline"]
                    if "maintenance" not in retained_baseline:
                        baseline.pop("maintenance", None)
                    if baseline != retained_baseline:
                        raise NativeControlError()
                generation = "sha256:" + digest(canonical_json(baseline))
                if state["phase"] == "pending" and state["adoption"] != generation:
                    raise NativeControlError()
                state["adoption"], state["phase"] = generation, "pending"
                _atomic(self.state_path, state)
                checkpoint("pending")
                directory = self.root / "runtime/native-control"
                directory.mkdir(exist_ok=True)
                guard, epoch = directory / "installation.guard", directory / "epoch"
                if not guard.exists():
                    with guard.open("xb") as stream:
                        stream.write(b"0")
                        stream.flush()
                        os.fsync(stream.fileno())
                checkpoint("guard")
                retired = {
                    "binding": self._binding(),
                    "baseline": baseline,
                    "generation": generation,
                }
                if state.get("retirement", retired) != retired:
                    raise NativeControlError()
                state["retirement"], state["successors"] = retired, []
                _atomic(self.state_path, state)
                expected = self._epoch(state)
                if epoch.exists() and _read_regular(
                    directory, "epoch", 256
                ) != expected.encode("ascii"):
                    raise NativeControlError()
                if not epoch.exists():
                    _atomic(epoch, expected)
                checkpoint("epoch")
                control = NativeControl(guard, epoch, expected)
                with control.exclusive():
                    # Original ingress + complete Jobs still held/verified here.
                    if self._legacy_closure(state) != "proven":
                        raise NativeControlError()
                    state["phase"] = "bound"
                    _atomic(self.state_path, state)
                    checkpoint("bound_state")
                    self._publish_head(state)
                    checkpoint("bound")
                return replace(entry, control=control)

    @contextmanager
    def operation(
        self,
        entry: NativeEntry,
        *,
        resolver: Callable[[], ManagedSelection],
        admission_held: Callable[[], bool],
        deadline: float | None = None,
    ) -> Iterator[NativeEntry]:
        """Retain native bound exclusion through all migration phases.

        Native shared is acquired before admission and excludes replacement.
        Bound state permanently refuses legacy starts under their ingress gate;
        retired managers are not required. Durable validation precedes admission.
        Resolver is rechecked inside the real gates at freeze/resume/cutover.
        """
        with entry.operation(deadline=deadline):
            state = self._state()
            if entry.control is None or state["phase"] != "bound":
                raise NativeControlError()
            selection = resolver()
            if (
                self._epoch(state) != entry.control.accepted_epoch
                or state["selection"] != selection.document()
                or self._closure(state) != "proven"
            ):
                raise NativeControlError()
            life = _LeaseLife(os.getpid(), threading.get_ident())
            proof = _HeldProof(
                self,
                entry,
                selection,
                resolver,
                admission_held,
                state["adoption"],
                state,
                life,
            )
            token = _HELD.set(proof)
            try:
                yield entry
            finally:
                life.active = False
                _HELD.reset(token)

    @contextmanager
    def replacement(
        self,
        entry: NativeEntry | _MaintenanceTarget,
        *,
        target_leaf: bytes,
        checkpoint: Callable[[str], None] = lambda _: None,
        _prepare: Callable[[], None] | None = None,
        _maintenance: dict[str, str] | None = None,
    ) -> Iterator[Callable[[bytes], Publication]]:
        if entry.control is None or _CONTROL_LEASE.get() is not None:
            raise NativeControlError()
        seal = leaf_seal(target_leaf)
        if seal is None:
            raise NativeControlError()
        with self._ingress():
            state = self._state()
            if state["phase"] != "bound":
                raise NativeControlError()
            self._durable(state)
            if entry.control.accepted_epoch != self._epoch(state):
                raise NativeControlError()
            with entry.control.exclusive():
                if _prepare is None:
                    if not isinstance(entry, NativeEntry):
                        raise NativeControlError()
                    self._publication(entry)
                else:
                    self._replacement_authority(entry, state)
                    # Once-only old Core planning happens under exclusion,
                    # before any durable fence or payload mutation.
                    _prepare()
                successor: dict[str, Any] = {
                    "from_archive": state["archive"],
                    "to_archive": seal[1],
                    "previous": state["adoption"],
                    "generation": "sha256:"
                    + digest(
                        canonical_json(
                            {"previous": state["adoption"], "archive": seal[1]}
                        )
                    ),
                }
                if _maintenance is not None:
                    successor["maintenance"] = _maintenance_record(_maintenance)
                    successor["generation"] = "sha256:" + digest(
                        canonical_json(
                            {
                                "previous": state["adoption"],
                                "archive": seal[1],
                                "maintenance": _maintenance,
                            }
                        )
                    )
                future = dict(
                    state,
                    archive=seal[1],
                    adoption=successor["generation"],
                    successors=[*state["successors"], successor],
                    replacement=None,
                    phase="bound",
                )
                state["phase"] = "updating"
                state["replacement"] = {
                    "successor": successor,
                    "old_epoch": self._epoch(state),
                    "new_epoch": self._epoch(future),
                }
                state["replacement"]["pending_epoch"] = self._pending_epoch(
                    state["replacement"]
                )
                # Shared primitives consult this bounded head. Publish refusal
                # BEFORE changing baseline, so manager death cannot expose the
                # old epoch in the baseline-before-epoch crash window.
                self._publish_head(state)
                checkpoint("updating_head")
                _atomic(self.state_path, state)
                checkpoint("updating_state")
                _atomic(entry.control.epoch_path, state["replacement"]["pending_epoch"])
                self._publish_head(state)
                checkpoint("updating")

                def publish(trusted_leaf: bytes) -> Publication:
                    if (
                        state["phase"] != "updating"
                        or _CONTROL_LEASE.get() is not entry.control
                        or not _native_life_held(entry.control)
                    ):
                        raise NativeControlError()
                    with _publication_read_exclusion(self.root):
                        publication = accept_publication(
                            self.root, trusted_leaf=trusted_leaf
                        )
                        if (
                            publication is None
                            or publication.projection_sha256 != seal[1]
                        ):
                            raise NativeControlError()
                        self._finish_replacement(state, publication, checkpoint)
                        return publication

                yield publish
                if state["phase"] != "bound":
                    raise NativeControlError()

    def _finish_replacement(
        self,
        state: dict[str, Any],
        publication: Publication,
        checkpoint: Callable[[str], None],
    ) -> None:
        record = state["replacement"]
        successor = record["successor"]
        if successor["to_archive"] != publication.projection_sha256 or (
            "maintenance" in successor
            and _maintenance_record(successor["maintenance"])["manifest_sha256"]
            != publication.manifest_sha256
        ):
            raise NativeControlError()
        future = dict(
            state,
            archive=successor["to_archive"],
            adoption=successor["generation"],
            successors=[*state["successors"], successor],
            replacement=None,
            phase="bound",
        )
        self._durable(future)
        if record["new_epoch"] != self._epoch(future):
            raise NativeControlError()
        _atomic(self.root / "runtime/native-control/epoch", record["new_epoch"])
        checkpoint("replacement_epoch")
        state.clear()
        state.update(future)
        _atomic(self.state_path, state)
        checkpoint("replacement_bound")
        self._publish_head(state)

    def recover_replacement(self, *, trusted_leaf: bytes) -> NativeEntry:
        seal = leaf_seal(trusted_leaf)
        if seal is None:
            raise NativeControlError()
        with self._ingress():
            state = self._state()
            if state["phase"] not in {"bound", "updating"}:
                raise NativeControlError()
            self._durable(state)
            expected = self._epoch(state)
            if state["phase"] == "updating":
                record = state["replacement"]
                if set(record) != {
                    "successor",
                    "old_epoch",
                    "new_epoch",
                    "pending_epoch",
                } or record["pending_epoch"] != self._pending_epoch(record):
                    raise NativeControlError()
                head = _read(self.directory / "adoption.json", 4096)
                if head != {
                    "installation": state["installation"],
                    "archive": state["archive"],
                    "generation": state["adoption"],
                    "phase": "updating",
                    "epoch": record["pending_epoch"],
                }:
                    raise NativeControlError()
                future = dict(
                    state,
                    archive=record["successor"]["to_archive"],
                    adoption=record["successor"]["generation"],
                    successors=[*state["successors"], record["successor"]],
                    phase="bound",
                    replacement=None,
                )
                self._durable(future)
                if (
                    record["old_epoch"] != expected
                    or record["new_epoch"] != self._epoch(future)
                    or seal[1] != future["archive"]
                ):
                    raise NativeControlError()
                accepted = {expected, record["pending_epoch"], record["new_epoch"]}
            else:
                accepted = {expected}
                if seal[1] != state["archive"]:
                    raise NativeControlError()
            directory = self.root / "runtime/native-control"
            epoch = _read_regular(directory, "epoch", 256).decode("ascii")
            if epoch not in accepted:
                raise NativeControlError()
            control = NativeControl(
                directory / "installation.guard", directory / "epoch", epoch
            )
            with control.exclusive():
                with _publication_read_exclusion(self.root):
                    publication = accept_publication(
                        self.root, trusted_leaf=trusted_leaf
                    )
                    if publication is None:
                        raise NativeControlError()
                    if state["phase"] == "updating":
                        self._finish_replacement(state, publication, lambda _: None)
                    else:
                        self._publish_head(state)
            return NativeEntry(
                self.root,
                publication,
                NativeImage.from_publication(self.root, publication),
                self._control(state),
            )

    def _legacy_closure(self, state: dict[str, Any]) -> str:
        if state.get("origin") == "cold-v1":
            return "unknown"
        """Query every reserved tree; empty launch list alone grants nothing."""
        if os.name != "nt":
            return "unknown"
        # A retained kernel sentinel proves continuity of the trusted manager.
        # If the manager died, do not reconstruct lifetime completeness from disk.
        kernel = _kernel()
        handle = kernel.OpenJobObjectW(4 | 8, False, state["sentinel"])
        if not handle:
            return "unknown"
        sentinel = OwnedJob(handle, state["sentinel"])
        try:
            if sentinel.active():
                return "unknown"
        finally:
            sentinel.close()
        slots: set[str] = set()
        active = False
        unknown = False
        for row in state["launches"]:
            try:
                slot = row["slot"]
                if (
                    not isinstance(slot, str)
                    or len(slot) != 32
                    or any(c not in "0123456789abcdef" for c in slot)
                    or slot in slots
                ):
                    raise NativeControlError()
                slots.add(slot)
                facts = _read(self.directory / (slot + ".json"))
                if facts.get("identity") != row["identity"]:
                    raise NativeControlError()
                job = reopen_job(facts, pid=facts["pid"], identity=row["identity"])
                if job is not None:
                    try:
                        active |= job.active() != 0
                    finally:
                        job.close()
            except (
                OSError,
                ValueError,
                KeyError,
                TypeError,
            ):
                unknown = True
        return "unknown" if unknown else "active" if active else "proven"

    def _binding(self) -> list[Any]:
        result: list[Any] = [str(self.root)]
        for ancestor in (
            *self.root.parents,
            self.root / "runtime",
            self.root / "runtime/native-control",
        ):
            info = ancestor.lstat()
            if (
                stat.S_ISLNK(info.st_mode)
                or getattr(info, "st_file_attributes", 0) & 0x400
            ):
                raise NativeControlError()
        for path in (
            self.root,
            self.directory,
            self.directory / "ingress.guard",
            self.root / "runtime/native-control/installation.guard",
        ):
            info = path.lstat()
            if (
                stat.S_ISLNK(info.st_mode)
                or getattr(info, "st_file_attributes", 0) & 0x400
            ):
                raise NativeControlError()
            result.append([info.st_dev, info.st_ino])
        return result

    def _epoch(self, state: dict[str, Any]) -> str:
        return "adopted-v2:" + digest(
            canonical_json(
                {
                    "retirement": state["retirement"],
                    "successors": state["successors"],
                    "archive": state["archive"],
                    "adoption": state["adoption"],
                }
            )
        )

    def _pending_epoch(self, record: dict[str, Any]) -> str:
        return "replacing:" + digest(
            canonical_json(
                {key: record[key] for key in ("successor", "old_epoch", "new_epoch")}
            )
        )

    def _durable(self, state: dict[str, Any]) -> None:
        retired = state["retirement"]
        if (
            type(state["schema"]) is not int
            or len(state["installation"]) != 32
            or any(c not in "0123456789abcdef" for c in state["installation"])
        ):
            raise NativeControlError()
        if (
            set(retired) != {"binding", "baseline", "generation"}
            or retired["binding"] != self._binding()
        ):
            raise NativeControlError()
        baseline = retired["baseline"]
        if not isinstance(baseline, dict) or not isinstance(state["successors"], list):
            raise NativeControlError()
        if state.get("origin") != "cold-v1" and set(baseline) - {
            "legacy_archive",
            "maintenance",
        } != {"installation", "archive", "selection", "sentinel", "launches"}:
            raise NativeControlError()
        keys: tuple[str, ...]
        if state.get("origin") == "cold-v1":
            _validate_cold_baseline(state, baseline)
            keys = ("installation", "selection", "origin")
        else:
            keys = ("installation", "selection", "sentinel", "launches")
        if any(state[key] != baseline[key] for key in keys):
            raise NativeControlError()
        if state.get("legacy_archive") != baseline.get("legacy_archive"):
            raise NativeControlError()
        generation = "sha256:" + digest(canonical_json(baseline))
        if generation != retired["generation"]:
            raise NativeControlError()
        if "maintenance" in baseline:
            _maintenance_record(baseline["maintenance"])
        archive = baseline["archive"]
        for successor in state["successors"]:
            if set(successor) - {"maintenance"} != {
                "from_archive",
                "to_archive",
                "previous",
                "generation",
            }:
                raise NativeControlError()
            commitment: dict[str, Any] = {
                "previous": generation,
                "archive": successor["to_archive"],
            }
            if "maintenance" in successor:
                commitment["maintenance"] = _maintenance_record(
                    successor["maintenance"]
                )
            expected = "sha256:" + digest(canonical_json(commitment))
            if (
                successor["from_archive"] != archive
                or successor["previous"] != generation
                or successor["generation"] != expected
            ):
                raise NativeControlError()
            archive, generation = successor["to_archive"], expected
        if state["archive"] != archive or state["adoption"] != generation:
            raise NativeControlError()
        if state["phase"] == "bound" and state["replacement"] is not None:
            raise NativeControlError()

    def _control(self, state: dict[str, Any]) -> NativeControl:
        self._durable(state)
        directory = self.root / "runtime/native-control"
        return NativeControl(
            directory / "installation.guard", directory / "epoch", self._epoch(state)
        )

    def attach(self, entry: NativeEntry, *, selection: ManagedSelection) -> NativeEntry:
        """Fresh independent entry; no creation/repair and no caller safety pins."""
        with self._ingress():
            state = self._state()
            if state["phase"] != "bound" or state["selection"] != selection.document():
                raise NativeControlError()
            control = self._control(state)
            with control.operation():
                publication = self._publication(entry)
                if publication.projection_sha256 != state["archive"]:
                    raise NativeControlError()
                head = _read(self.directory / "adoption.json", 4096)
                if head != {
                    "installation": state["installation"],
                    "archive": state["archive"],
                    "generation": state["adoption"],
                    "phase": "bound",
                    "epoch": self._epoch(state),
                }:
                    raise NativeControlError()
            return replace(entry, control=control)


def _managed_storage_safety(
    entry: NativeEntry, context: Any
) -> tuple[str, str, tuple[str, ...]]:
    """Actual NativeEntry adapter; no caller-provided proven MigrationSafety."""
    proof = _HELD.get()
    if (
        proof is None
        or not proof.life.live()
        or proof.entry is not entry
        or not _native_life_held(entry.control)
        or not proof.admission_held()
    ):
        return "unknown", "", ("managed_exclusion_not_held",)
    try:
        # Durable validation completed before admission. Native shared excludes
        # replacement; bound state refuses all declared legacy launch ingresses.
        state = proof.state
        head = _read(proof.producer.directory / "adoption.json", 4096)
        selected = proof.resolver()
        if (
            head
            != {
                "installation": state["installation"],
                "archive": state["archive"],
                "generation": state["adoption"],
                "phase": "bound",
                "epoch": entry.control.accepted_epoch
                if entry.control is not None
                else "",
            }
            or selected != proof.selection
            or str(context.project_root or "") != selected.project
            or str(context.workplace_root or "") != selected.workplace
            or not set(
                (t.kind, str(t.target), t.scope, t.owner_id) for t in context.targets
            ).issubset(selected.targets)
            or entry.control is None
            or _CONTROL_LEASE.get() is not entry.control
            or _read_regular(entry.control.epoch_path.parent, "epoch", 256)
            != entry.control.accepted_epoch.encode("ascii")
        ):
            raise NativeControlError()
        return (
            "proven",
            proof.generation,
            (
                "native_bound_operation_held",
                "durable_cold_retirement"
                if state.get("origin") == "cold-v1"
                else "durable_retired_legacy_set",
                "accepted_archive:" + state["archive"],
                "adoption:" + proof.generation,
            ),
        )
    except (
        OSError,
        ValueError,
        KeyError,
        TypeError,
    ):
        return "unknown", "", ("managed_revalidation_failed",)


def _durable_control(root: Path, archive: str) -> NativeControl:
    """Pre-Core control selection. Pending/updating never expose raw old lease."""
    producer = ManagedEnrollmentProducer(root, b"")
    state = producer._state()
    if state["phase"] != "bound" or state["archive"] != archive:
        raise NativeControlError()
    return producer._control(state)


def _bootstrap_control(
    root: Path, archive: str, guard: Path, epoch: Path
) -> NativeControl | None:
    """Pending before native guard creation is already a durable refusal."""
    producer = ManagedEnrollmentProducer(root, b"")
    if producer.state_path.exists():
        state = producer._state()
        if state["phase"] != "legacy":
            return _durable_control(root, archive)
        if guard.exists() or epoch.exists():
            raise NativeControlError()
    if guard.exists():
        return _durable_control(root, archive)
    return None


def _validate_shared_head(control: NativeControl) -> None:
    """Bounded phase check under the OS lease, including raw child leases.

    Enrollment/recovery use exclusive primitives. Generic ingress gates have a
    different guard filename. Domain execution always requires a shared lease.
    """
    if control.guard.name != "installation.guard":
        return
    try:
        head = _read(
            control.guard.parent.parent / "managed-ingress/adoption.json", 4096
        )
        if (
            set(head) != {"installation", "archive", "generation", "phase", "epoch"}
            or head["phase"] != "bound"
            or head["epoch"] != control.accepted_epoch
        ):
            raise NativeControlError()
    except (
        OSError,
        ValueError,
        KeyError,
        TypeError,
    ):
        raise NativeControlError() from None


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


class NativeUpdateError(Exception):
    """Carry existing updater errors without invoking retired Core handlers."""

    def __init__(self, code: str, message: str) -> None:
        self.code, self.message = code, message
        super().__init__(message)


def _update_atomic(path: Path, raw: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".pf-update-tmp")
    with _PHYSICAL_OPEN(temporary, "wb") as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)


def _update_json(path: Path, value: Mapping[str, Any]) -> None:
    _update_atomic(path, (json.dumps(value, indent=2, sort_keys=True) + "\n").encode())


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


def replace_core(
    entry: NativeEntry | _MaintenanceTarget,
    archive_path: Path,
    prepare: Callable[[], dict[str, Any]],
    *,
    workplace_root: Path | None,
) -> dict[str, Any]:
    """Replace exclusively, then surrender all parent writes to a fresh child.

    prepare is the existing Core planner, called exactly once under exclusion,
    before the native engine writes anything. It must return only plain data
    after its domain/SQL/diagnostic scopes unwind. No callback runs thereafter.
    G1 enrollment must already have qualified entry.control and its owner set.
    """
    import base64
    import shutil
    import zipfile

    if entry.control is None or (
        isinstance(entry, NativeEntry)
        and (entry.publication is None or entry.image is None)
    ):
        raise NativeControlError()
    root = entry.root
    producer = ManagedEnrollmentProducer(
        root,
        entry.publication.payload[LEAF]
        if isinstance(entry, NativeEntry) and entry.publication
        else b"",
    )
    try:
        with _PHYSICAL_OPEN(archive_path, "rb") as stream:
            archive_raw = stream.read(MAX_TOTAL + MAX_MANIFEST + 1)
        if len(archive_raw) > MAX_TOTAL + MAX_MANIFEST:
            raise NativeControlError()
        with zipfile.ZipFile(io.BytesIO(archive_raw)) as archive:
            selected_manifest = parse_manifest(archive.read(MANIFEST))
        frozen = _freeze_update_archive(
            archive_raw, {"new_manifest": selected_manifest}
        )
    except zipfile.BadZipFile as error:
        raise NativeUpdateError("archive_invalid", "invalid ZIP archive") from error
    except (Refusal, KeyError) as error:
        raise NativeControlError() from error
    plan: dict[str, Any] = {}
    maintenance: dict[str, str] = {}

    def prepare_once() -> None:
        token = _UPDATE_PLAN_ENTRY.set(entry)
        try:
            plan.update(prepare())
        finally:
            _UPDATE_PLAN_ENTRY.reset(token)
        if plan["new_manifest"] != selected_manifest:
            raise NativeControlError()
        maintenance.update(
            _maintenance_record(
                {
                    "manifest_sha256": digest(frozen.manifest),
                    "device_config_path": plan["_native_device_config_path"],
                }
            )
        )
        # The full qualified archive supplies every replaced byte. Remaining
        # owned paths must already match it; collision/containment guards remain.
        writes = set(plan["added"]) | set(plan["changed"]) | set(plan["restored"])
        removed = set(plan["removed"])
        for relative, raw in frozen.payload.items():
            # A removed owned file may be the new directory's ancestor.
            if any(parent.as_posix() in removed for parent in Path(relative).parents):
                continue
            target = _update_target(root, relative)
            if target.exists() and target.is_file() and target.stat().st_nlink != 1:
                raise NativeControlError()
            if (
                relative not in writes
                and _read_regular(root, relative, len(raw)) != raw
            ):
                raise NativeControlError()
        for relative in removed:
            target = _update_target(root, relative)
            if target.exists() and target.is_file() and target.stat().st_nlink != 1:
                raise NativeControlError()

    with producer.replacement(
        entry,
        target_leaf=frozen.payload[LEAF],
        _prepare=prepare_once,
        _maintenance=maintenance,
    ) as publish:
        update_id = "core-update-" + _update_now().replace(":", "").replace("-", "")
        work = root / "runtime/core-update"
        backup = work / "backups" / update_id
        backup.mkdir(parents=True, exist_ok=False)
        progress_path = work / "in-progress.json"
        restored = set(plan["restored"])
        backup_paths = sorted(set(plan["removed"]) | set(plan["changed"]) | restored)
        write_paths = sorted(set(plan["added"]) | set(plan["changed"]) | restored)
        migration = plan.get("workplace_migration") or {}
        pending = (
            [{"op": "backup", "path": p} for p in backup_paths]
            + [{"op": "delete", "path": p} for p in plan["removed"]]
            + [{"op": "write", "path": p} for p in write_paths]
            + [{"op": "write_manifest", "path": MANIFEST}]
        )
        migration_id = str((migration.get("migration") or {}).get("id") or "workplace")
        if migration.get("status") == "planned" and migration.get("operations"):
            pending.append({"op": "workplace_migration", "path": migration_id})
        backed_up: dict[str, str | None] = {}
        progress: dict[str, Any] = {
            "schema_version": 1,
            "update_id": update_id,
            "status": "applying",
            "started_at": _update_now(),
            "core_root": str(root),
            "archive": str(archive_path),
            "backup_dir": str(backup),
            "installed_version": plan.get("installed_version"),
            "target_version": plan.get("available_version"),
            "counts": plan["counts"],
            "completed_operations": [],
            "pending_operations": pending,
            "backed_up": backed_up,
        }

        def complete(op: str, path: str) -> None:
            progress["completed_operations"].append(
                {"op": op, "path": path, "completed_at": _update_now()}
            )
            pending.remove({"op": op, "path": path})
            _update_json(progress_path, progress)

        try:
            old_manifest = _read_regular(root, MANIFEST, MAX_MANIFEST)
            _update_atomic(backup / "control/old-manifest.json", old_manifest)
            _update_atomic(backup / "control/new-manifest.json", frozen.manifest)
            _update_json(
                backup / "control/plan.json",
                {k: v for k, v in plan.items() if k != "new_manifest"},
            )
            _update_json(progress_path, progress)
            for relative in backup_paths:
                source = _update_target(root, relative)
                target = backup / "files" / relative
                if source.is_file():
                    target.parent.mkdir(parents=True, exist_ok=True)
                    with (
                        _PHYSICAL_OPEN(source, "rb") as incoming,
                        _PHYSICAL_OPEN(target, "wb") as outgoing,
                    ):
                        shutil.copyfileobj(incoming, outgoing)
                        outgoing.flush()
                        os.fsync(outgoing.fileno())
                    shutil.copystat(source, target)
                    backed_up[relative] = target.relative_to(backup).as_posix()
                else:
                    backed_up[relative] = None
                complete("backup", relative)
            # Durable producer pending head/epoch already excludes old readers.
            for relative in plan["removed"]:
                target = _update_target(root, relative)
                target.unlink(missing_ok=True)
                parent = target.parent
                while parent != root:
                    try:
                        parent.rmdir()
                    except OSError:
                        break
                    parent = parent.parent
                complete("delete", relative)
            for relative in write_paths:
                _update_atomic(_update_target(root, relative), frozen.payload[relative])
                complete("write", relative)
            _update_atomic(root / MANIFEST, frozen.manifest)
            complete("write_manifest", MANIFEST)
            if _read_regular(root, LEAF, MAX_FILE) != frozen.payload[LEAF]:
                raise NativeControlError()
            installed = accept_publication(root, trusted_leaf=frozen.payload[LEAF])
            if installed is None or installed.manifest_sha256 != digest(
                frozen.manifest
            ):
                raise NativeControlError()
            publish(frozen.payload[LEAF])
            successor = producer._state()
            handoff = {
                "schema_version": 1,
                "root": str(root),
                "epoch": producer._epoch(successor),
                "generation": successor["adoption"],
                "selection": successor["selection"],
                "manifest_sha256": digest(frozen.manifest),
                "leaf_sha256": digest(frozen.payload[LEAF]),
                "leaf": base64.b64encode(frozen.payload[LEAF]).decode("ascii"),
                "archive": base64.b64encode(archive_raw).decode("ascii"),
                "archive_sha256": digest(archive_raw),
                "workplace_root": str(workplace_root) if workplace_root else None,
                "device_config_path": str(plan["_native_device_config_path"]),
                "configuration": plan["_native_configuration"],
                "progress": progress,
                "migration": migration,
                "migration_id": migration_id,
                "available_version": plan["available_version"],
            }
        except Exception as error:
            # Only captured stdlib leaf code writes after the first overwrite.
            progress.update(
                status="failed",
                failed_at=_update_now(),
                error={"code": "file_operation_failed", "message": str(error)},
            )
            try:
                _update_json(progress_path, progress)
            except OSError:
                pass
            raise NativeUpdateError("file_operation_failed", str(error)) from error
    # No parent lease survives here. The child independently acquires before
    # accepting payload/importing Core; a racing publication causes refusal.
    return _launch_update_child(handoff)


_UPDATE_CHILD_BOOTSTRAP = """import base64,json,sys,types
data=json.load(sys.stdin)
leaf=base64.b64decode(data["leaf"],validate=True)
module=types.ModuleType("pf_native_control")
module.__file__=data["root"]+"/tools/pf_native_control.py"
module._captured_source=leaf
sys.modules[module.__name__]=module
exec(compile(leaf,module.__file__,"exec",dont_inherit=True),module.__dict__)
module._run_update_child(data)
"""


def _launch_update_child(
    handoff: dict[str, Any], *, timeout: float = 210
) -> dict[str, Any]:
    try:
        child = subprocess.run(
            [sys.executable, "-I", "-B", "-c", _UPDATE_CHILD_BOOTSTRAP],
            input=json.dumps(handoff),
            text=True,
            encoding="utf-8",
            errors="strict",
            capture_output=True,
            shell=False,
            timeout=timeout,
        )
        result = json.loads(child.stdout)
        if child.returncode != 0 or not isinstance(result, dict):
            raise ValueError("post-update child refused")
        if "_update_error" in result:
            error = result["_update_error"]
            raise NativeUpdateError(error["code"], error["message"])
        if handoff.get("phase") in {"doctor", "storage"}:
            return result
        if result.get("update_id") != handoff["progress"]["update_id"]:
            raise ValueError("post-update child identity mismatch")
        return result
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        # Parent does not repair/write old last-apply, diagnostics or domains.
        raise NativeUpdateError(
            "file_operation_failed", "post-update child unavailable"
        ) from error


def _run_update_child(data: dict[str, Any]) -> None:
    """Own an independent lease before capture/import through the final write."""
    import base64

    global _ENTRY
    root = Path(data["root"])
    trusted_leaf = getattr(sys.modules[__name__], "_captured_source")
    seal = leaf_seal(trusted_leaf)
    if (
        data.get("schema_version") != 1
        or seal is None
        or digest(trusted_leaf) != data["leaf_sha256"]
    ):
        raise NativeControlError()
    for path in (root, *root.parents):
        info = path.lstat()
        if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & 0x400:
            raise NativeControlError()
    producer = ManagedEnrollmentProducer(root, trusted_leaf)
    control = _durable_control(root, seal[1])
    if control.accepted_epoch != data["epoch"]:
        raise NativeControlError()
    with control.operation():
        successor = producer._state()
        if (
            successor["adoption"] != data["generation"]
            or successor["selection"] != data["selection"]
            or producer._epoch(successor) != data["epoch"]
        ):
            raise NativeControlError()
        # Publication epochs can repeat on a same-byte reinstall. Bind this
        # finalizer to the exact durable update, not just the publication hash.
        if data.get("phase") not in {"doctor", "storage"}:
            progress = json.loads(
                _read_regular(
                    root, "runtime/core-update/in-progress.json", MAX_MANIFEST
                )
            )
            if (
                progress.get("update_id") != data["progress"]["update_id"]
                or progress.get("status") != "applying"
            ):
                raise NativeControlError()
        if _read_regular(root, LEAF, MAX_FILE) != trusted_leaf:
            raise NativeControlError()
        publication = accept_publication(root, trusted_leaf=trusted_leaf)
        if (
            publication is None
            or publication.manifest_sha256 != data["manifest_sha256"]
        ):
            raise NativeControlError()
        archive_raw = base64.b64decode(data["archive"], validate=True)
        if digest(archive_raw) != data["archive_sha256"]:
            raise NativeControlError()
        image = NativeImage.from_publication(root, publication)
        image.activate()
        _ENTRY = NativeEntry(root, publication, image, control)
        sys.path[:0] = [str(root / "tools"), str(root / "src")]
        from processforge_core.composition import _update_selection

        maintenance = _accepted_maintenance(successor)
        if (
            maintenance is None
            or maintenance["manifest_sha256"] != publication.manifest_sha256
            or maintenance["device_config_path"] != data["device_config_path"]
        ):
            raise NativeControlError()
        # Re-read external configuration/owners before any child domain write.
        with _update_selection(
            successor["selection"],
            Path(maintenance["device_config_path"]),
            workplace_root=Path(data["workplace_root"])
            if data["workplace_root"]
            else None,
        ):
            pass
        if data.get("phase") in {"doctor", "storage"}:
            result = _update_action(data)
        else:
            try:
                result = _finish_update_child(data, archive_raw)
            except Exception as error:
                failure = {
                    "code": getattr(error, "code", "file_operation_failed"),
                    "message": getattr(error, "message", str(error)),
                }
                data["progress"].update(
                    status="failed", failed_at=_update_now(), error=failure
                )
                try:
                    _update_json(
                        root / "runtime/core-update/in-progress.json", data["progress"]
                    )
                except OSError:
                    pass
                result = {"_update_error": failure}
        print(json.dumps(result, indent=2, sort_keys=True))


def _finish_update_child(data: dict[str, Any], archive_raw: bytes) -> dict[str, Any]:
    """Run only new Core code under the child's live operation lease."""
    from processforge_core.maintenance.update import apply_workplace_migration

    progress = data["progress"]
    root, backup = Path(data["root"]), Path(progress["backup_dir"])
    work = root / "runtime/core-update"
    migration = data["migration"]
    workplace = Path(data["workplace_root"]) if data["workplace_root"] else None
    migration_record = None
    if migration.get("status") == "planned" and migration.get("operations"):
        if workplace is None:
            raise NativeUpdateError(
                "workplace_root_missing",
                "Workplace migration was planned without a Workplace root",
            )
        # ZipFile accepts BytesIO: no reread of the mutable operator archive.
        archive_source: Any = io.BytesIO(archive_raw)
        from processforge_core.composition import _update_selection

        with _update_selection(
            data["selection"],
            Path(data["device_config_path"]),
            workplace_root=workplace,
        ):
            migration_record = apply_workplace_migration(
                archive_source, workplace, migration, backup
            )
        item = {"op": "workplace_migration", "path": data["migration_id"]}
        progress["pending_operations"].remove(item)
        progress["completed_operations"].append({**item, "completed_at": _update_now()})
        _update_json(work / "in-progress.json", progress)
    record = {
        "schema_version": 1,
        "update_id": progress["update_id"],
        "status": "applied",
        "applied_at": _update_now(),
        "available_version": data["available_version"],
        "backup_dir": str(backup),
        "backed_up": progress["backed_up"],
        "counts": progress["counts"],
        "workplace_migration": migration_record,
    }
    _update_json(work / "last-apply.json", record)
    (work / "in-progress.json").unlink(missing_ok=True)
    if workplace is not None:
        record["post_update_doctor"] = _update_doctor(data, root, workplace)
        _update_json(work / "last-apply.json", record)
    return record


def _update_action(data: dict[str, Any]) -> dict[str, Any]:
    import contextlib
    import importlib.util

    root = Path(data["root"])
    workplace = str(data["workplace_root"])
    doctor = data["phase"] == "doctor"
    script = "tools/processforge.py" if doctor else "tools/migrate-storage.py"
    arguments = (
        ["doctor-workplace", "--root", workplace]
        if doctor
        else [
            "--workplace-root",
            workplace,
            "--apply",
            "--json",
            "--device-config",
            data["device_config_path"],
        ]
    )
    output = io.StringIO()
    with contextlib.redirect_stdout(output), contextlib.redirect_stderr(output):
        try:
            # spec_from_file_location is the existing captured image loader;
            # runpy/open_code or a fresh disk/pyc script loader is not used.
            spec = importlib.util.spec_from_file_location(
                "_pf_update_" + data["phase"], root / script
            )
            if spec is None or spec.loader is None:
                raise NativeControlError()
            module = importlib.util.module_from_spec(spec)
            sys.modules[spec.name] = module
            spec.loader.exec_module(module)
            from processforge_core.configuration import ConfigurationProvider, PFConfig
            from processforge_core.project.configuration_inputs import (
                configuration_operation,
            )

            pinned = ConfigurationProvider.pinned(
                PFConfig.from_dict(data["configuration"])
            )
            with configuration_operation(
                None,
                Path(workplace),
                device_config_path=Path(data["device_config_path"]),
                configuration=pinned,
            ):
                from processforge_core.composition import _update_selection

                with _update_selection(
                    data["selection"],
                    Path(data["device_config_path"]),
                    workplace_root=Path(workplace),
                ):
                    if doctor:
                        code = module.main(arguments)
                    else:
                        code = module.main(
                            arguments, configuration_builder=lambda **_: pinned
                        )
        except SystemExit as exit_value:
            code = exit_value.code if isinstance(exit_value.code, int) else 1
    result: dict[str, Any] = {"exit_code": code, "output": output.getvalue()}
    if not doctor:
        storage = json.loads(output.getvalue())
        if not isinstance(storage, dict):
            raise ValueError("storage_result_invalid")
        result["result"] = storage
    return result


def _update_doctor(data: dict[str, Any], root: Path, workplace: Path) -> dict[str, Any]:
    # Each action is a fresh independently leased process with its original
    # 90-second bound, nested under the fresh supervisor's operation lease.
    command = [
        sys.executable,
        str(root / "bin/pf.py"),
        "doctor-workplace",
        "--root",
        str(workplace),
    ]
    try:
        doctor = _launch_update_child({**data, "phase": "doctor"}, timeout=90)
        result: dict[str, Any] = {
            "status": "pass" if doctor["exit_code"] == 0 else "fail",
            "command": command,
            "output": doctor["output"],
        }
    except NativeUpdateError as error:
        result = {"status": "fail", "command": command, "output": str(error)}
    try:
        storage = _launch_update_child({**data, "phase": "storage"}, timeout=90)
        result["storage_migration"] = {
            "exit_code": storage["exit_code"],
            "result": storage["result"],
        }
        if storage["exit_code"] != 0:
            result["status"] = "fail"
    except NativeUpdateError:
        result["storage_migration"] = {
            "error": {"code": "storage_migration_unavailable"}
        }
        result["status"] = "fail"
    return result


def _cold_require(condition: bool) -> None:
    if not condition:
        raise NativeControlError()


def _validate_cold_baseline(state: dict[str, Any], baseline: dict[str, Any]) -> None:
    """Pure post-bound validation: no controller import, discovery or OS scan."""
    _cold_require(
        set(baseline) - {"maintenance"}
        == {"origin", "installation", "archive", "selection", "cold"}
    )
    _cold_require(baseline["origin"] == "cold-v1")
    cold = baseline["cold"]
    _cold_require(
        set(cold)
        == {
            "transaction",
            "archive",
            "policy",
            "namespace",
            "retirement",
            "fence_commitment",
        }
    )
    _cold_require(cold["transaction"] == state["installation"])
    _cold_require(bool(re.fullmatch(r"sha256:[a-f0-9]{64}", cold["archive"])))
    _cold_require(bool(re.fullmatch(r"[a-f0-9]{64}", cold["fence_commitment"])))
    profile = cold["policy"]
    _cold_require(
        set(profile) == {"maintenance", "normal", "versions", "qualification"}
    )
    _cold_require(
        bool(profile["normal"])
        and len(set(profile["normal"])) == len(profile["normal"])
    )
    for sid in [profile["maintenance"], *profile["normal"]]:
        _cold_require(bool(re.fullmatch(r"S-1-(?:[0-9]+-)*[0-9]+", sid)))
    _cold_require(profile["maintenance"] not in {*profile["normal"], "S-1-5-18"})
    _cold_require("S-1-5-18" not in profile["normal"])
    saved = cold["retirement"]
    _cold_require(set(saved) == {"kind", "before", "after", "qualification"})
    _cold_require(saved["kind"] == "qualified-native-tick-reset-v1")
    _cold_require(saved["qualification"] == profile["qualification"])
    _cold_require(bool(re.fullmatch(r"sha256:[a-f0-9]{64}", profile["qualification"])))
    for sample in (saved["before"], saved["after"]):
        _cold_require(set(sample) == {"low", "high", "checked", "version"})
        _cold_require(sample["checked"] is False)
        _cold_require(type(sample["low"]) is int and type(sample["high"]) is int)
        _cold_require(0 <= sample["low"] <= sample["high"] < 2**63)
        _cold_require(sample["version"] in profile["versions"])
    _cold_require(saved["before"]["version"] == saved["after"]["version"])
    _cold_require(saved["after"]["high"] + 60000 < saved["before"]["low"])


def _run_cold_child(data: dict[str, Any]) -> None:
    """Independently leased native-only cold finalizer; no target Core imports."""
    import base64

    leaf = getattr(sys.modules[__name__], "_captured_source")
    _cold_require(digest(leaf) == data["leaf_sha256"])
    root = Path(data["root"])
    seal = leaf_seal(leaf)
    if seal is None:
        raise NativeControlError()
    producer = ManagedEnrollmentProducer(root, leaf)
    control = _durable_control(root, seal[1])
    _cold_require(control.accepted_epoch == data["epoch"])
    with control.operation():
        state = producer._state()
        _cold_require(state.get("origin") == "cold-v1" and state["phase"] == "bound")
        _cold_require(state["installation"] == data["transaction"])
        _cold_require(
            state["adoption"] == data["generation"]
            and state["selection"] == data["selection"]
        )
        publication = accept_publication(root, trusted_leaf=leaf)
        if (
            publication is None
            or publication.manifest_sha256 != data["manifest_sha256"]
        ):
            raise NativeControlError()
        _cold_require(_read_regular(root, LEAF, MAX_FILE) == leaf)
        import zipfile

        archive = base64.b64decode(data["archive_raw"], validate=True)
        _cold_require("sha256:" + digest(archive) == data["archive"])
        with zipfile.ZipFile(io.BytesIO(archive)) as package:
            manifest = package.read(MANIFEST)
        frozen = _freeze_update_archive(
            archive, {"new_manifest": parse_manifest(manifest)}
        )
        _cold_require(digest(manifest) == data["manifest_sha256"])
        _cold_require(publication.payload == frozen.payload)
        _cold_require(
            state["retirement"]["baseline"]["cold"]["archive"] == data["archive"]
        )
        result = {
            key: data[key]
            for key in (
                "transaction",
                "generation",
                "epoch",
                "selection",
                "archive",
                "token",
            )
        }
        result.update(
            manifest=data["manifest_sha256"],
            leaf=data["leaf_sha256"],
            result="verified",
        )
        print(json.dumps(result, sort_keys=True))
