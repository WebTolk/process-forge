"""Bounded, non-destructive scratch observation and cheap last-report reads."""

from __future__ import annotations

import json
import os
import stat
import time
import uuid
from contextlib import ExitStack, contextmanager
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath

from ..configuration.models import TemporaryFilesConfig

PERIOD_SECONDS = 3600
MAX_ENTRIES = 2000
MAX_DEPTH = 16
TIME_BUDGET_SECONDS = 0.1
MAX_CANDIDATES = 20
MAX_REPORT_BYTES = 65536
MAX_PATH_BYTES = 1024
STATES = {"notify", "off", "missing", "partial", "error"}
REASONS = {
    "entry_limit",
    "depth_limit",
    "time_limit",
    "link_boundary",
    "access_error",
    "unsafe_directory",
    "path_limit",
    "observation_failed",
}
COUNTS = (
    "files_count_lower_bound",
    "bytes_lower_bound",
    "candidate_count_lower_bound",
    "candidate_bytes_lower_bound",
    "entries_observed",
)


def _linked(info) -> bool:
    return stat.S_ISLNK(info.st_mode) or bool(
        getattr(info, "st_file_attributes", 0) & 0x400
    )


@contextmanager
def _directory(
    path: Path,
    parent: int | None = None,
    *,
    expected_identity: tuple[int, int] | None = None,
):
    """Never traverse a directory link, including a replacement during the walk.

    POSIX walks use open directory descriptors and O_NOFOLLOW. Windows pins
    each ancestor without delete sharing before using scandir on its path.
    OPEN_REPARSE_POINT makes the handle check cover junctions as well as links.
    Owned disposal binds the opened object to its recorded identity before yield.
    """
    if os.name == "nt":
        import ctypes
        from ctypes import wintypes

        kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        create = kernel.CreateFileW
        create.argtypes = [
            wintypes.LPCWSTR,
            wintypes.DWORD,
            wintypes.DWORD,
            ctypes.c_void_p,
            wintypes.DWORD,
            wintypes.DWORD,
            wintypes.HANDLE,
        ]
        create.restype = wintypes.HANDLE
        close = kernel.CloseHandle
        close.argtypes, close.restype = [wintypes.HANDLE], wintypes.BOOL
        query = kernel.GetFileInformationByHandleEx
        query.argtypes = [
            wintypes.HANDLE,
            ctypes.c_int,
            ctypes.c_void_p,
            wintypes.DWORD,
        ]
        query.restype = wintypes.BOOL
        # LIST_DIRECTORY participates in sharing checks; attributes alone do not
        # reliably prevent a directory rename on Windows.
        handle = create(str(path), 0x81, 3, None, 3, 0x02200000, None)
        if handle == wintypes.HANDLE(-1).value:
            raise ctypes.WinError(ctypes.get_last_error())
        try:
            attributes = (wintypes.DWORD * 2)()
            if not query(
                handle, 9, ctypes.byref(attributes), ctypes.sizeof(attributes)
            ):
                raise ctypes.WinError(ctypes.get_last_error())
            if attributes[0] & 0x400 or not attributes[0] & 0x10:
                raise OSError("unsafe_directory")
            if expected_identity is not None:

                class FileId(ctypes.Structure):
                    _fields_ = [
                        ("volume", ctypes.c_ulonglong),
                        ("identity", ctypes.c_ubyte * 16),
                    ]

                file_id = FileId()
                if not query(handle, 18, ctypes.byref(file_id), ctypes.sizeof(file_id)):
                    raise ctypes.WinError(ctypes.get_last_error())
                identity = (
                    file_id.volume,
                    int.from_bytes(bytes(file_id.identity), "little"),
                )
                if identity != expected_identity:
                    raise ValueError("identity_changed")
            yield None
        finally:
            close(handle)
    else:
        if not hasattr(os, "O_DIRECTORY") or not hasattr(os, "O_NOFOLLOW"):
            raise OSError("safe_directory_operations_unavailable")
        descriptor = os.open(
            path.name if parent is not None else path,
            os.O_RDONLY | os.O_DIRECTORY | getattr(os, "O_NOFOLLOW"),
            dir_fd=parent,
        )
        try:
            info = os.fstat(descriptor)
            if not stat.S_ISDIR(info.st_mode):
                raise OSError("unsafe_directory")
            if (
                expected_identity is not None
                and (info.st_dev, info.st_ino) != expected_identity
            ):
                raise ValueError("identity_changed")
            yield descriptor
        finally:
            os.close(descriptor)


def _base(config: TemporaryFilesConfig, now: float) -> dict:
    return {
        "schema_version": 1,
        "kind": "pf.temporary_files",
        "root": ".pf/tmp",
        "observed_at": datetime.fromtimestamp(now, timezone.utc).isoformat(),
        "configuration": asdict(config),
        "state": "notify",
        "reasons": [],
        **dict.fromkeys(COUNTS, 0),
        "candidate_paths": [],
    }


def observe(
    project_root: Path, config: TemporaryFilesConfig, *, now: float | None = None
) -> dict:
    """Observe metadata only. Counts/bytes are lower bounds, never a deletion list.

    The deadline bounds admission to filesystem operations, not the duration of
    an individual OS call. Handles and iterators close on all early returns.
    """
    now = time.time() if now is None else now
    report = _base(config, now)
    if config.mode == "off":
        report["state"] = "off"
        return report
    root = Path(project_root).absolute()
    scratch = root / ".pf/tmp"
    deadline = time.monotonic() + TIME_BUDGET_SECONDS

    def partial(reason):
        report["state"] = "partial"
        if reason not in report["reasons"]:
            report["reasons"].append(reason)

    def exhausted():
        if report["entries_observed"] >= MAX_ENTRIES:
            partial("entry_limit")
            return True
        if time.monotonic() >= deadline:
            partial("time_limit")
            return True
        return False

    def walk(directory: Path, descriptor: int | None, depth: int):
        with os.scandir(descriptor if descriptor is not None else directory) as entries:
            while not exhausted():
                entry = next(entries, None)
                if entry is None:
                    break
                report["entries_observed"] += 1
                try:
                    info = entry.stat(follow_symlinks=False)
                    if _linked(info):
                        partial("link_boundary")
                    elif stat.S_ISDIR(info.st_mode):
                        if depth >= MAX_DEPTH:
                            partial("depth_limit")
                        elif not exhausted():
                            child = directory / entry.name
                            with _directory(child, descriptor) as child_descriptor:
                                walk(child, child_descriptor, depth + 1)
                    elif stat.S_ISREG(info.st_mode):
                        report["files_count_lower_bound"] += 1
                        report["bytes_lower_bound"] += info.st_size
                        if info.st_mtime <= now - config.max_age_hours * 3600:
                            report["candidate_count_lower_bound"] += 1
                            report["candidate_bytes_lower_bound"] += info.st_size
                            candidate = (
                                (directory / entry.name).relative_to(scratch).as_posix()
                            )
                            if not _valid_candidate(candidate):
                                partial("path_limit")
                            elif len(report["candidate_paths"]) < MAX_CANDIDATES:
                                report["candidate_paths"].append(candidate)
                except OSError:
                    partial("access_error")

    try:
        with _directory(root) as project_descriptor:
            with _directory(root / ".pf", project_descriptor) as pf_descriptor:
                with _directory(scratch, pf_descriptor) as scratch_descriptor:
                    walk(scratch, scratch_descriptor, 0)
    except FileNotFoundError:
        report["state"] = "missing"
    except OSError as exc:
        report["state"] = "error"
        report["reasons"] = [
            "unsafe_directory" if str(exc) == "unsafe_directory" else "access_error"
        ]
    return report


@contextmanager
def report_destination(project_root: Path, *, create: bool = False):
    """Pin report ancestors; POSIX operations must use the returned descriptor."""
    root = Path(project_root).absolute()
    with ExitStack() as stack:
        descriptor = stack.enter_context(_directory(root))
        directory = root
        for name in (".pf", "runtime", "maintenance"):
            directory = directory / name
            if create and name != ".pf":
                try:
                    if os.name == "nt":
                        directory.mkdir()
                    else:
                        os.mkdir(name, dir_fd=descriptor)
                except FileExistsError:
                    pass
            descriptor = stack.enter_context(_directory(directory, descriptor))
        yield directory / "temporary-files.json", descriptor


def write_report(project_root: Path, report: dict, *, atomic_writer) -> None:
    """Publish beside the pinned destination; preserve the Windows writer."""
    with report_destination(project_root, create=True) as (path, parent):
        if os.name == "nt":
            atomic_writer(path, report)
            return
        if parent is None:
            raise OSError("unsafe_directory")
        staging = f".{path.name}.{os.getpid()}.{uuid.uuid4().hex}.tmp"
        created = False
        try:
            # O_EXCL rejects preexisting links; unsupported dir_fd/NOFOLLOW
            # primitives fail closed without falling back to absolute paths.
            fd = os.open(
                staging,
                os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW"),
                0o666,
                dir_fd=parent,
            )
            created = True
            with os.fdopen(fd, "w", encoding="utf-8") as stream:
                stream.write(
                    json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True)
                    + "\n"
                )
            os.replace(staging, path.name, src_dir_fd=parent, dst_dir_fd=parent)
        except BaseException:
            if created:
                try:
                    os.unlink(staging, dir_fd=parent)
                except (OSError, NotImplementedError):
                    pass  # Cleanup denial must not mask the publication error.
            raise


def _valid_candidate(value) -> bool:
    if not isinstance(value, str):
        return False
    try:
        length = len(value.encode("utf-8"))
    except UnicodeError:
        return False
    return (
        0 < length <= MAX_PATH_BYTES
        and not any(ord(char) < 32 for char in value)
        and "\\" not in value
        and ":" not in value
        and not value.startswith("/")
        and all(part not in {"", ".", ".."} for part in value.split("/"))
        and not PurePosixPath(value).is_absolute()
    )


def _read_report(project_root: Path) -> dict:
    with report_destination(project_root) as (path, parent):
        if os.name != "nt" and parent is None:
            raise OSError("unsafe_directory")
        info = (
            path.lstat()
            if os.name == "nt"
            else os.stat(path.name, dir_fd=parent, follow_symlinks=False)
        )
        if _linked(info) or not stat.S_ISREG(info.st_mode):
            raise ValueError("report_invalid")
        flags = os.O_RDONLY | getattr(os, "O_NONBLOCK", 0)
        if os.name != "nt":
            flags |= getattr(os, "O_NOFOLLOW")
        fd = os.open(path.name if parent is not None else path, flags, dir_fd=parent)
        with os.fdopen(fd, "rb") as stream:
            opened = os.fstat(stream.fileno())
            if (opened.st_dev, opened.st_ino) != (
                info.st_dev,
                info.st_ino,
            ) or not stat.S_ISREG(opened.st_mode):
                raise ValueError("report_invalid")
            raw = stream.read(MAX_REPORT_BYTES + 1)
    if len(raw) > MAX_REPORT_BYTES:
        raise ValueError("report_invalid")
    report = json.loads(raw)
    if (
        not isinstance(report, dict)
        or report.get("kind") != "pf.temporary_files"
        or type(report.get("schema_version")) is not int
        or report["schema_version"] != 1
        or report.get("root") != ".pf/tmp"
        or report.get("state") not in STATES
        or any(type(report.get(key)) is not int or report[key] < 0 for key in COUNTS)
        or report["entries_observed"] > MAX_ENTRIES
        or report["candidate_count_lower_bound"] > report["files_count_lower_bound"]
        or report["files_count_lower_bound"] > report["entries_observed"]
        or report["candidate_bytes_lower_bound"] > report["bytes_lower_bound"]
        or not isinstance(report.get("candidate_paths"), list)
        or len(report["candidate_paths"]) > MAX_CANDIDATES
        or len(report["candidate_paths"]) > report["candidate_count_lower_bound"]
        or any(not _valid_candidate(path) for path in report["candidate_paths"])
        or not isinstance(report.get("reasons"), list)
        or len(report["reasons"]) > len(REASONS)
        or any(
            not isinstance(reason, str) or reason not in REASONS
            for reason in report["reasons"]
        )
    ):
        raise ValueError("report_invalid")
    recorded = report.get("configuration")
    if not isinstance(recorded, dict) or set(recorded) != {
        "mode",
        "max_age_hours",
        "retain_unused",
    }:
        raise ValueError("report_invalid")
    TemporaryFilesConfig(**recorded)
    stamp = datetime.fromisoformat(report["observed_at"])
    if stamp.tzinfo is None:
        raise ValueError("report_invalid")
    report["timestamp"] = stamp.timestamp()
    return report


def last_summary(
    project_root: Path, config: TemporaryFilesConfig, *, now: float | None = None
) -> dict:
    """No scratch walk, Runtime discovery, writes, or candidate-path exposure."""
    result = {
        "status": "unknown",
        "notification": False,
        "configuration": asdict(config),
    }
    if config.mode == "off":
        return dict(result, status="off")
    try:
        report = _read_report(project_root)
    except FileNotFoundError:
        return dict(result, reason="report_missing")
    except (OSError, ValueError, TypeError, KeyError, OverflowError, RecursionError):
        return dict(result, reason="report_invalid")
    age = (time.time() if now is None else now) - report["timestamp"]
    if age < 0:
        return dict(result, reason="report_time_invalid")
    result.update(observed_at=report["observed_at"], age_seconds=age)
    if report["configuration"] != asdict(config):
        return dict(result, status="stale", reason="configuration_changed")
    if age >= PERIOD_SECONDS:
        return dict(result, status="stale", reason="report_expired")
    result.update(
        status=report["state"],
        reasons=report["reasons"],
        **{key: report[key] for key in COUNTS},
    )
    result["notification"] = (
        report["state"] in {"notify", "partial"}
        and report["candidate_count_lower_bound"] > 0
    )
    return result


def observation_age(project_root: Path) -> float | None:
    """Respect an existing observation across app-server restarts/config changes."""
    try:
        age = time.time() - _read_report(project_root)["timestamp"]
        return age if age >= 0 else None
    except (OSError, ValueError, TypeError, KeyError, OverflowError, RecursionError):
        return None


def failed_observation(config: TemporaryFilesConfig) -> dict:
    report = _base(config, time.time())
    report.update(state="error", reasons=["observation_failed"])
    return report
