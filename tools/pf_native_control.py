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
import time
import unicodedata
from collections.abc import Iterator, Mapping
from contextlib import AbstractContextManager, ExitStack, contextmanager
from contextvars import ContextVar
from ctypes import wintypes
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Any
from uuid import uuid4

_PHYSICAL_OPEN = io.open


class NativeControlError(OSError):
    """Refuse an operation whose exact native ownership cannot be established."""

    def __init__(self) -> None:
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
        process = subprocess.Popen(argv, env=environment, **options)
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
        except (TypeError, ValueError):
            return None

    @classmethod
    def from_publication(cls, root: Path, publication: Publication) -> NativeImage:
        """Use the exact verified capture; never reopen code after acceptance."""
        image = cls.__new__(cls)
        image.root = root.resolve(strict=True)
        image.files = MappingProxyType(dict(publication.payload))
        image._active = False
        return image

    def read(self, relative: str) -> bytes:
        try:
            return self.files[relative]
        except KeyError:
            raise NativeControlError() from None

    def activate(self) -> None:
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
        if any(
            name == "processforge_core" or name.startswith("processforge_core.")
            for name in sys.modules
        ):
            raise NativeControlError()
        image = self
        original_spec = importlib.util.spec_from_file_location
        original_open, original_io_open = builtins.open, io.open

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
            if relative is None or relative.startswith("runtime/"):
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
            stream = self.guard.open("r+b", buffering=0)
            locked = False
            token = None
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
                token = _CONTROL_LEASE.set(self)
                yield self
            finally:
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


def accept_publication(root: Path, *, trusted_leaf: bytes) -> Publication | None:
    """Verify before Core, outside guard; None keeps recognized legacy mode.

    No guard/epoch/runtime directory is created. Caller holds actual deployment
    exclusion, validates the root's ancestors, supplies the source bytes it
    compiled as the trusted leaf, and retains the returned bytes for all loads.
    A caller-supplied current-file pin is not a trust source for this function.
    """
    seal = leaf_seal(trusted_leaf)
    if seal is None:
        return None
    try:
        raw = _read_regular(root, MANIFEST, MAX_MANIFEST)
        data = parse_manifest(raw)
        if digest(projection(raw)) != seal[1]:
            raise Refusal("publication_drift")
        captured: dict[str, bytes] = {}
        for row in data["files"]:
            path = row["relative_path"]
            content = (
                trusted_leaf if path == LEAF else _read_regular(root, path, row["size"])
            )
            if len(content) != row["size"] or digest(content) != row["sha256"]:
                raise Refusal("payload_drift")
            captured[path] = content
        if captured.get(INVENTORY) != inventory_bytes(captured):
            raise Refusal("derived_inventory_drift")
        return Publication(MappingProxyType(captured), seal[1], digest(raw))
    except OSError as exc:
        raise Refusal("publication_unreadable") from exc


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
        from contextlib import contextmanager

        @contextmanager
        def held() -> Iterator[NativeEntry]:
            if self.control is None:
                # No authority to migrate follows from an unadopted publication.
                yield self
            elif _CONTROL_LEASE.get() is self.control:
                yield self
            else:
                with self.control.operation(deadline=deadline):
                    yield self

        return held()


_ENTRY: NativeEntry | None = None


def bootstrap_entry(root: Path, *, trusted_leaf: bytes) -> NativeEntry:
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
    control = NativeControl(guard, epoch, seal[1]) if guard.exists() else None
    from contextlib import ExitStack

    with ExitStack() as leases:
        if control is not None:
            leases.enter_context(control.operation())
        else:
            leases.enter_context(_publication_read_exclusion(root))
        if _read_regular(root, LEAF, MAX_FILE) != trusted_leaf:
            raise NativeControlError()
        publication = accept_publication(root, trusted_leaf=trusted_leaf)
        if publication is None:
            raise NativeControlError()
        image = NativeImage.from_publication(root, publication)
    image.activate()
    _ENTRY = NativeEntry(root, publication, image, control)
    return _ENTRY


def current_entry() -> NativeEntry | None:
    """Return the already accepted native entry without discovery or I/O."""
    return _ENTRY


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
