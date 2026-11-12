"""Interprocess admission primitives; runtime policy remains in host composition."""

from __future__ import annotations

import errno
import json
import math
import os
import socket
import subprocess
import sys
import threading
import time
import uuid
from collections.abc import Callable, Iterator
from contextlib import AbstractContextManager, contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from .. import diagnostics
from ..common.clock import now_utc
from ..executions.model import ExecutionError
from ..project.metadata import ProjectMetadataReader


def _registry_lock_try_os_lock(fd: int) -> bool:
    """Take a non-blocking advisory lock on an open registry lock file."""

    try:
        if sys.platform == "win32":
            import msvcrt

            os.lseek(fd, 0, os.SEEK_SET)
            msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)
        else:
            import fcntl

            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except ImportError as error:
        raise OSError(errno.ENOSYS, "registry lock backend unavailable") from error
    except OSError as error:
        # Only a competing byte/flock owner warrants a retry. A broken backend,
        # invalid descriptor or access failure must retain its original cause.
        if error.errno in {errno.EACCES, errno.EAGAIN, errno.EWOULDBLOCK} and (
            sys.platform != "win32" or getattr(error, "winerror", None) in {None, 33}
        ):
            return False
        raise
    return True


def _registry_lock_owner_alive(owner: dict[str, Any]) -> bool | None:
    """Return liveness, or None when ownership cannot be safely assessed."""

    owner_host = str(owner.get("host") or "")
    if owner_host and owner_host != socket.gethostname():
        return None
    try:
        pid = int(owner["pid"])
    except (KeyError, TypeError, ValueError):
        return None
    if pid <= 0:
        return None
    if "linux_identity" in owner:
        if not sys.platform.startswith("linux"):
            return None
        from processforge_platforms.linux_process_identity import lock_owner_alive

        return lock_owner_alive(owner)
    if sys.platform == "win32":
        try:
            import ctypes

            kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
            from ctypes import wintypes

            kernel32.OpenProcess.argtypes = [
                wintypes.DWORD,
                wintypes.BOOL,
                wintypes.DWORD,
            ]
            kernel32.OpenProcess.restype = wintypes.HANDLE
            kernel32.GetExitCodeProcess.argtypes = [
                wintypes.HANDLE,
                ctypes.POINTER(wintypes.DWORD),
            ]
            kernel32.GetExitCodeProcess.restype = wintypes.BOOL
            kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
            kernel32.CloseHandle.restype = wintypes.BOOL
            handle = kernel32.OpenProcess(
                0x1000, False, pid
            )  # PROCESS_QUERY_LIMITED_INFORMATION
            if not handle:
                # ERROR_INVALID_PARAMETER means that the PID is gone. Other
                # failures (notably access denied) remain conservatively live.
                return ctypes.get_last_error() != 87
            exit_code = ctypes.c_ulong()
            try:
                if not kernel32.GetExitCodeProcess(handle, ctypes.byref(exit_code)):
                    return True
                return exit_code.value == 259  # STILL_ACTIVE
            finally:
                kernel32.CloseHandle(handle)
        except (AttributeError, OSError, TypeError, ValueError):
            pass
        try:
            result = subprocess.run(
                ["tasklist", "/FI", f"PID eq {pid}", "/FO", "CSV", "/NH"],
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                text=True,
                shell=False,
                timeout=5,
            )
        except (OSError, subprocess.SubprocessError):
            return True
        output = result.stdout or ""
        if str(pid) in output:
            return True
        # A failed or access-denied tasklist query is not proof of death.
        # Only the explicit no-match response permits stale recovery.
        if result.returncode == 0 and "no tasks are running" in output.lower():
            return False
        return True
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except OSError:
        return True
    return True


def _registry_lock_stale(
    owner: dict[str, Any], lock_path: Path, stale_after_seconds: float
) -> bool:
    try:
        created_at = str(owner["created_at"])
        created = datetime.fromisoformat(created_at.replace("Z", "+00:00")).timestamp()
        age = time.time() - created
    except (KeyError, TypeError, ValueError, OverflowError, OSError):
        try:
            age = time.time() - lock_path.stat().st_mtime
        except OSError:
            return False
    return age > stale_after_seconds


def _registry_lock_read_owner(lock_path: Path) -> dict[str, Any] | None:
    try:
        value = json.loads(lock_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return value if isinstance(value, dict) else None


@contextmanager
def registry_file_lock(
    path: Path, *, timeout_seconds: float = 30.0, stale_after_seconds: float = 300.0
) -> Iterator[None]:
    path.parent.mkdir(parents=True, exist_ok=True)
    lock_path = path.with_name(f".{path.name}.lock")
    # Never unlink this guard: all new writers and stale-owner recovery must
    # lock the same inode, including across Windows close-before-unlink.
    guard_path = path.with_name(f".{path.name}.lock.guard")
    guard_fd = os.open(str(guard_path), os.O_CREAT | os.O_RDWR, 0o600)
    deadline = time.monotonic() + timeout_seconds
    owner = {
        "path": str(path),
        "pid": os.getpid(),
        "host": socket.gethostname(),
        "created_at": now_utc(),
        "token": uuid.uuid4().hex,
    }
    acquired = False

    def wait_for_owner(phase: str) -> None:
        if time.monotonic() >= deadline:
            error = SystemExit(
                f"FAIL: registry is locked by another writer: {lock_path}"
            )
            error.__dict__.update(
                registry_lock_reason="contention_timeout", registry_lock_phase=phase
            )
            raise error
        time.sleep(min(0.1, max(0.0, deadline - time.monotonic())))

    try:
        if sys.platform.startswith("linux"):
            from processforge_platforms.linux_process_identity import (
                lock_owner_identity,
            )

            owner.update(lock_owner_identity())
        while not _registry_lock_try_os_lock(guard_fd):
            wait_for_owner("guard")
        while True:
            try:
                fd = os.open(
                    str(lock_path), os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600
                )
            except FileExistsError:
                existing = _registry_lock_read_owner(lock_path)
                if (
                    existing
                    and _registry_lock_stale(existing, lock_path, stale_after_seconds)
                    and _registry_lock_owner_alive(existing) is False
                ):
                    # The persistent guard serializes reapers with acquisition
                    # and release. Unknown/foreign/live legacy owners stay put.
                    if _registry_lock_read_owner(lock_path) == existing:
                        try:
                            lock_path.unlink()
                        except FileNotFoundError:
                            pass
                        continue
                wait_for_owner("owner")
                continue
            try:
                with os.fdopen(fd, "w", encoding="utf-8") as handle:
                    json.dump(owner, handle, ensure_ascii=False, sort_keys=True)
                    handle.write("\n")
                    handle.flush()
                    os.fsync(handle.fileno())
            except BaseException:
                lock_path.unlink(missing_ok=True)
                raise
            acquired = True
            break
        yield
    finally:
        try:
            if acquired and _registry_lock_read_owner(lock_path) == owner:
                lock_path.unlink(missing_ok=True)
        finally:
            os.close(guard_fd)


@dataclass
class _GateLease:
    key: tuple[int, int, Path]
    active: bool = True

    def is_current(self) -> bool:
        return self.active and self.key[:2] == (os.getpid(), threading.get_ident())


_HELD_GATES: ContextVar[tuple[_GateLease, ...]] = ContextVar(
    "execution_admission_gates", default=()
)


_PENDING_FAILURE: ContextVar[ExecutionError | None] = ContextVar(
    "execution_admission_failure", default=None
)


# Synchronous emit only: thread-local state cannot leak into copied contexts.
_EMITTING_FAILURE = threading.local()


def _flush_admission_failure() -> None:
    # Defer nested project failures until the workplace gate also unwinds.
    if any(lease.is_current() for lease in _HELD_GATES.get()):
        return
    error = _PENDING_FAILURE.get()
    _PENDING_FAILURE.set(None)
    if error is not None and not getattr(_EMITTING_FAILURE, "active", False):
        _EMITTING_FAILURE.active = True
        try:
            diagnostics.emit(
                "error",
                "runtime.admission.failed",
                {"exception": error},
                component="runtime",
            )
        except BaseException:
            # Even an unavailable/hostile optional logger cannot affect admission.
            pass
        finally:
            _PENDING_FAILURE.set(None)
            _EMITTING_FAILURE.active = False


class ExecutionAdmission:
    """Reuse the host's permanent-guard registry lock without importing tools.

    Gate order is workplace, project, existing task lock, SQL transaction.
    The caller verifies enrollment, readiness, instance and stopping fence inside
    the gate; these locks themselves grant no routing or launch permission.
    Shutdown holds the workplace gate while the caller validates instance/routing,
    takes sorted project gates and publishes durable stopping before release.
    No memory lock may be held while waiting to acquire these gates.
    """

    def __init__(
        self,
        registry_lock: Callable[
            ..., AbstractContextManager[object]
        ] = registry_file_lock,
    ) -> None:
        self.registry_lock = registry_lock

    @contextmanager
    def _gate(self, path: Path, deadline: float | None) -> Iterator[None]:
        timeout = 30.0
        if deadline is not None:
            if not math.isfinite(deadline):
                raise ValueError("invalid deadline")
            timeout = min(timeout, deadline - time.monotonic())
            if timeout <= 0:
                raise ExecutionError("execution_activity_unknown")
        key = (os.getpid(), threading.get_ident(), path.absolute())
        held = tuple(lease for lease in _HELD_GATES.get() if lease.is_current())
        if any(lease.key == key for lease in held):
            yield
            return
        operation_error: BaseException | None = None
        phase = "acquire"
        try:
            with self.registry_lock(
                path, timeout_seconds=timeout, stale_after_seconds=0
            ):
                if deadline is not None and time.monotonic() >= deadline:
                    raise ExecutionError("execution_activity_unknown")
                lease = _GateLease(key)
                token = _HELD_GATES.set((*held, lease))
                try:
                    yield
                except BaseException as exc:
                    # contextlib throws the operation's exception back at yield.
                    # Remember its identity before the lock unwinds so only our
                    # own admission/acquisition/release errors are normalized.
                    operation_error = exc
                    raise
                finally:
                    # Copies borrow the same lease; invalidate every copy on exit.
                    lease.active = False
                    _HELD_GATES.reset(token)
                    phase = "release"
        except (OSError, TimeoutError, SystemExit) as exc:
            if exc is operation_error:
                raise
            error = ExecutionError("execution_activity_unknown")
            # These bounded internal facts survive normalization without placing
            # the registry's private path/message in CLI or MCP error payloads.
            facts = diagnostics.admission_facts(exc)
            error.__dict__.update(
                admission_reason=facts.get(
                    "registry_lock_reason",
                    "timeout"
                    if isinstance(exc, TimeoutError)
                    else "lock_exit"
                    if isinstance(exc, SystemExit)
                    else "lock_io_error",
                ),
                admission_phase=phase,
                registry_lock_phase=facts.get("registry_lock_phase"),
                admission_errno=facts.get("errno"),
                admission_winerror=facts.get("winerror"),
            )
            # Only the normalized message and safe facts accompany the original
            # traceback. Never pass the lock message/path to optional logging.
            error = error.with_traceback(exc.__traceback__)
            _PENDING_FAILURE.set(error)
            raise error from None
        finally:
            _flush_admission_failure()

    @contextmanager
    def start(
        self,
        project_root: Path,
        workplace_root: Path | None,
        *,
        deadline: float | None = None,
    ) -> Iterator[None]:
        """Serialize reservation with shutdown/registration using one budget.

        Enrollment resolution is mandatory before calling; an enrolled project
        must never supply None merely because its workplace is unavailable.
        """
        project_gate = (
            ProjectMetadataReader(project_root).flow_root()
            / "runtime"
            / "execution-admission"
        )
        if workplace_root is None:
            with self._gate(project_gate, deadline):
                yield
        else:
            with self._gate(
                workplace_root / "runtime" / "pf-runtime" / "execution-admission",
                deadline,
            ):
                with self._gate(project_gate, deadline):
                    try:
                        self.check_stopping(workplace_root)
                    except (OSError, TimeoutError, SystemExit):
                        raise ExecutionError("execution_activity_unknown") from None
                    if deadline is not None and time.monotonic() >= deadline:
                        raise ExecutionError("execution_activity_unknown")
                    yield

    @contextmanager
    def shutdown(
        self, workplace_root: Path, *, expected_instance_id: str, deadline: float
    ) -> Iterator[None]:
        """Hold workplace admission for the caller's exact-instance shutdown check.

        Expected instance is required, but only the host can compare it to its
        authoritative state. This primitive does not clear/recover a stopping
        owner or infer death from elapsed time.
        """
        if (
            not isinstance(expected_instance_id, str)
            or not expected_instance_id.strip()
            or "\x00" in expected_instance_id
        ):
            raise ExecutionError("execution_activity_unknown")
        with self._gate(
            workplace_root / "runtime" / "pf-runtime" / "execution-admission", deadline
        ):
            yield

    @contextmanager
    def maintenance(
        self, project_root: Path, workplace_root: Path | None
    ) -> Iterator[None]:
        """Acquire the same gates for explicit maintenance/binding publication."""
        with self.workplace(workplace_root):
            with self.project(project_root):
                yield

    @contextmanager
    def workplace(
        self, workplace_root: Path | None, *, deadline: float | None = None
    ) -> Iterator[None]:
        """Acquire workplace before project gates for registration/maintenance."""
        if workplace_root is None:
            yield
        else:
            with self._gate(
                workplace_root / "runtime/pf-runtime/execution-admission", deadline
            ):
                yield

    @contextmanager
    def project(
        self, project_root: Path, *, deadline: float | None = None
    ) -> Iterator[None]:
        """Take one project gate inside an already held workplace gate."""
        with self._gate(
            ProjectMetadataReader(project_root).flow_root()
            / "runtime/execution-admission",
            deadline,
        ):
            yield

    @staticmethod
    def held(project_root: Path | None, workplace_root: Path | None) -> bool:
        """Observe actual operation-local gate ownership, never file metadata."""
        paths = []
        if workplace_root is not None:
            paths.append(workplace_root / "runtime/pf-runtime/execution-admission")
        if project_root is not None:
            paths.append(
                ProjectMetadataReader(project_root).flow_root()
                / "runtime/execution-admission"
            )
        held = {lease.key for lease in _HELD_GATES.get() if lease.is_current()}
        return bool(paths) and all(
            (os.getpid(), threading.get_ident(), path.absolute()) in held
            for path in paths
        )

    @staticmethod
    def check_stopping(workplace_root: Path) -> None:
        """Honor a durable stopping fence; invalid state never permits a start.

        This is a refusal fence, not host quiescence proof. Only the existing
        singleton recovery protocol can clear a dead or stopped instance.
        """
        from ..runtime_service_state import SERVICE_STATE_MAX_BYTES

        path = workplace_root / "runtime/pf-runtime/service.json"
        try:
            with path.open("rb") as stream:
                raw = stream.read(SERVICE_STATE_MAX_BYTES + 1)
        except FileNotFoundError:
            return
        except OSError:
            raise ExecutionError("execution_activity_unknown") from None
        try:
            if len(raw) > SERVICE_STATE_MAX_BYTES:
                raise ValueError

            def pairs(items: list[tuple[str, object]]) -> dict[str, object]:
                result: dict[str, object] = {}
                for key, value in items:
                    if key in result:
                        raise ValueError("duplicate state key")
                    result[key] = value
                return result

            def constant(value: str) -> object:
                raise ValueError("nonfinite state value")

            state = json.loads(raw, object_pairs_hook=pairs, parse_constant=constant)
            if not isinstance(state, dict) or state.get("status") not in {
                "starting",
                "ready",
                "running",
                "stopped",
                "stale",
                "stopping",
                "failed",
            }:
                raise ValueError
            if state["status"] in {"stopping", "failed"}:
                raise ExecutionError("execution_activity_unknown")
        except (OSError, ValueError, TypeError):
            raise ExecutionError("execution_activity_unknown") from None
