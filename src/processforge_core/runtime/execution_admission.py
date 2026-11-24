"""Interprocess admission primitives; runtime policy remains in host composition."""

from __future__ import annotations

import errno
import json
import math
import os
import re
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
from functools import lru_cache
from pathlib import Path
from typing import Any, Literal

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


@lru_cache(maxsize=128)
def _registry_guard_signal(pid: int, guard_path: Path) -> threading.Condition:
    """Notify local waiters; an evicted signal falls back to the OS-lock retry."""
    return threading.Condition(threading.Lock())


@dataclass(frozen=True)
class PreparedRegistryOwner:
    """Platform identity to collect before entering an admitted section."""

    fields: dict[str, Any]


def prepare_registry_owner() -> PreparedRegistryOwner:
    fields = {"pid": os.getpid(), "host": socket.gethostname()}
    if sys.platform.startswith("linux"):
        from processforge_platforms.linux_process_identity import lock_owner_identity

        fields.update(lock_owner_identity())
    return PreparedRegistryOwner(fields)


def _registry_lock_paths(path: Path) -> tuple[Path, Path]:
    path.parent.mkdir(parents=True, exist_ok=True)
    # All writers and reapers must use the same permanent guard inode.
    return (
        path.with_name(f".{path.name}.lock"),
        path.with_name(f".{path.name}.lock.guard"),
    )


def _registry_create_marker(path: Path) -> int:
    return os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)


def _registry_remove_marker(path: Path, primary: BaseException | None) -> None:
    try:
        path.unlink(missing_ok=True)
    except OSError as error:
        if primary is None:
            raise
        primary.add_note(f"registry_lock_owner_cleanup_failed:{type(error).__name__}")


@contextmanager
def _registry_publish_marker(
    fd: int, marker: Path, path: Path, prepared: PreparedRegistryOwner
) -> Iterator[None]:
    try:
        owner = {
            **prepared.fields,
            "path": str(path),
            "created_at": now_utc(),
            "token": uuid.uuid4().hex,
        }
        stream = os.fdopen(fd, "wb")
    except BaseException as error:
        try:
            os.close(fd)
        except OSError as cleanup:
            error.add_note(
                f"registry_lock_marker_close_failed:{type(cleanup).__name__}"
            )
        _registry_remove_marker(marker, error)
        raise
    try:
        with stream:
            # Preserve the newline previously supplied by text-mode translation.
            payload = (
                json.dumps(owner, ensure_ascii=False, sort_keys=True) + os.linesep
            ).encode("utf-8")
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
    except BaseException as error:
        _registry_remove_marker(marker, error)
        raise

    primary: BaseException | None = None
    try:
        yield
    except BaseException as error:
        primary = error
        raise
    finally:
        if _registry_marker_bytes(marker) == payload:
            _registry_remove_marker(marker, primary)


RegistryTryResult = Literal["acquired", "guard_busy", "owner_marker"]
RegistryWaitAssessment = Literal[
    "guard_busy", "owner_live", "owner_dead", "owner_unknown", "deadline_expired"
]
_RegistryOwnerObservation = tuple[bytes | None, RegistryWaitAssessment]


class RegistryLockTimeout(TimeoutError):
    """Deadline expired with the last contention assessment, when observed."""

    def __init__(
        self, phase: Literal["guard", "owner"], assessment: RegistryWaitAssessment
    ) -> None:
        super().__init__(f"registry_lock_timeout:{phase}:{assessment}")
        self.phase = phase
        self.assessment = assessment


@contextmanager
def _open_registry_guard(path: Path) -> Iterator[int]:
    fd = os.open(path, os.O_CREAT | os.O_RDWR, 0o600)
    primary: BaseException | None = None
    try:
        yield fd
    except BaseException as error:
        primary = error
        raise
    finally:
        try:
            os.close(fd)
        except OSError as error:
            if primary is None:
                raise
            primary.add_note(f"registry_lock_guard_close_failed:{type(error).__name__}")


@contextmanager
def try_registry_file_lock(
    path: Path, *, owner: PreparedRegistryOwner
) -> Iterator[RegistryTryResult]:
    """Try once without inspecting a competing marker or waiting for a guard."""
    marker, guard = _registry_lock_paths(path)
    with _open_registry_guard(guard) as guard_fd:
        if not _registry_lock_try_os_lock(guard_fd):
            miss: RegistryTryResult = "guard_busy"
        else:
            try:
                marker_fd = _registry_create_marker(marker)
            except FileExistsError:
                miss = "owner_marker"
            else:
                with _registry_publish_marker(marker_fd, marker, path, owner):
                    yield "acquired"
                return
    yield miss


def _selected_registry_owner_alive(owner: dict[str, Any]) -> bool | None:
    """Return only positive presence or absence, with unknown for unusable evidence."""
    pid, host, token = owner.get("pid"), owner.get("host"), owner.get("token")
    limit = 0xFFFFFFFF if sys.platform == "win32" else 0x7FFFFFFF
    if (
        type(pid) is not int
        or not 1 <= pid <= limit
        or not isinstance(host, str)
        or not host.strip()
        or host != socket.gethostname()
        or not isinstance(token, str)
        or not token.strip()
        or "\x00" in token
    ):
        return None
    if "linux_identity" in owner:
        value = owner["linux_identity"]
        if not sys.platform.startswith("linux") or not isinstance(value, dict):
            return None
        device, boot, ticks = (
            value.get("procfs_device"),
            value.get("boot_id"),
            value.get("start_ticks"),
        )
        if (
            not isinstance(device, str)
            or not device.isascii()
            or not device.isdecimal()
            or not isinstance(boot, str)
            or re.fullmatch(r"[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}", boot)
            is None
            or not isinstance(ticks, str)
            or not ticks.isascii()
            or not ticks.isdecimal()
            or not ticks.lstrip("0")
        ):
            return None
        from processforge_platforms.linux_process_identity import lock_owner_alive

        return lock_owner_alive(owner)
    if sys.platform == "win32":
        from .process_identity import capture_process

        try:
            return capture_process(pid, require_running=True) is not None
        except (ExecutionError, OSError):
            return None
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except OSError:
        return None
    return True


def _registry_marker_bytes(marker: Path) -> bytes | None:
    try:
        return marker.read_bytes()
    except OSError:
        return None


def _assess_registry_marker(
    marker: Path,
    previous: _RegistryOwnerObservation,
    *,
    deadline: float,
    stale_after_seconds: float,
) -> _RegistryOwnerObservation | None:
    """Return the observed owner assessment, or None after reclaiming its marker."""
    raw = _registry_marker_bytes(marker)
    if raw is None:
        return None, "owner_unknown"
    try:
        owner = json.loads(raw.decode("utf-8"))
    except ValueError:
        return raw, "owner_unknown"
    if not isinstance(owner, dict):
        return raw, "owner_unknown"
    if time.monotonic() >= deadline:
        # Exact bytes keep a changed marker from borrowing the previous proof.
        return previous if previous[0] == raw else (raw, "owner_unknown")
    alive = _selected_registry_owner_alive(owner)
    if alive is None:
        return raw, "owner_unknown"
    if alive:
        return raw, "owner_live"
    if (
        time.monotonic() < deadline
        and _registry_lock_stale(owner, marker, stale_after_seconds)
        and _registry_marker_bytes(marker) == raw
        and time.monotonic() < deadline
    ):
        marker.unlink(missing_ok=True)
        return None
    return raw, "owner_dead"


@contextmanager
def wait_registry_file_lock(
    path: Path,
    *,
    deadline: float,
    stale_after_seconds: float = 300.0,
    on_contention: Callable[[], None] | None = None,
) -> Iterator[None]:
    """Wait outside admission and retain the attempt's terminal assessment."""
    if not math.isfinite(deadline):
        raise ValueError("registry deadline must be finite")
    if time.monotonic() >= deadline:
        raise RegistryLockTimeout("guard", "deadline_expired")
    owner = prepare_registry_owner()
    marker, guard = _registry_lock_paths(path)
    delay = 0.001
    previous: _RegistryOwnerObservation = (None, "owner_unknown")
    while True:
        phase: Literal["guard", "owner"] = "guard"
        assessment: RegistryWaitAssessment = "guard_busy"
        with _open_registry_guard(guard) as guard_fd:
            locked = _registry_lock_try_os_lock(guard_fd)
            while locked:
                if time.monotonic() >= deadline:
                    raise RegistryLockTimeout("guard", "deadline_expired")
                try:
                    marker_fd = _registry_create_marker(marker)
                except FileExistsError:
                    phase = "owner"
                    observed = _assess_registry_marker(
                        marker,
                        previous,
                        deadline=deadline,
                        stale_after_seconds=stale_after_seconds,
                    )
                    if observed is not None:
                        previous = observed
                        assessment = observed[1]
                        break
                    previous = (None, "owner_unknown")
                else:
                    with _registry_publish_marker(marker_fd, marker, path, owner):
                        if time.monotonic() >= deadline:
                            raise RegistryLockTimeout("owner", "deadline_expired")
                        yield
                    return
        if on_contention is not None:
            on_contention()
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise RegistryLockTimeout(phase, assessment)
        time.sleep(min(delay, remaining))
        if time.monotonic() >= deadline:
            raise RegistryLockTimeout(phase, assessment)
        delay = min(delay * 2, 0.1)


@contextmanager
def registry_file_lock(
    path: Path,
    *,
    timeout_seconds: float = 30.0,
    stale_after_seconds: float = 300.0,
    on_contention: Callable[[], None] | None = None,
) -> Iterator[None]:
    lock_path, guard_path = _registry_lock_paths(path)
    signal = _registry_guard_signal(os.getpid(), guard_path.absolute())
    deadline = time.monotonic() + timeout_seconds
    retry_delay = 0.001

    def wait_for_owner(phase: str) -> None:
        nonlocal retry_delay
        if on_contention is not None:
            on_contention()
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            error = SystemExit(
                f"FAIL: registry is locked by another writer: {lock_path}"
            )
            error.__dict__.update(
                registry_lock_reason="contention_timeout", registry_lock_phase=phase
            )
            raise error
        delay = min(retry_delay, remaining)
        if phase == "guard":
            signal.wait(delay)
        else:
            time.sleep(delay)
        retry_delay = min(retry_delay * 2, 0.1)

    # Close the guard before notifying legacy waiters.
    try:
        with _open_registry_guard(guard_path) as guard_fd:
            owner = prepare_registry_owner()
            with signal:
                while not _registry_lock_try_os_lock(guard_fd):
                    wait_for_owner("guard")
            while True:
                try:
                    fd = _registry_create_marker(lock_path)
                except FileExistsError:
                    existing = _registry_lock_read_owner(lock_path)
                    if (
                        existing
                        and _registry_lock_stale(
                            existing, lock_path, stale_after_seconds
                        )
                        and _registry_lock_owner_alive(existing) is False
                        and _registry_lock_read_owner(lock_path) == existing
                    ):
                        lock_path.unlink(missing_ok=True)
                        continue
                    wait_for_owner("owner")
                else:
                    break
            with _registry_publish_marker(fd, lock_path, path, owner):
                yield
    finally:
        with signal:
            signal.notify()


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

    Blocking gate order is workplace, project, existing task lock, SQL transaction.
    A retained task proof may only try outer gates without waiting; contention
    must release the task and proof before retrying acquisition.
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
