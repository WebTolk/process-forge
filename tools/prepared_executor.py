#!/usr/bin/env python3
"""Lifecycle wrapper for a ProcessForge prepared-input worker invocation.

The wrapper validates the private prepared-input pointer and digest, then runs
an explicit argv target with inherited stdio/cwd and no shell or PF bootstrap.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Any, Sequence

# Capture the stdlib-only native leaf before any Core/adapter import. Python's
# -B flag does not prevent execution of an existing unchecked bytecode cache.
_native_root = Path(__file__).absolute().parents[1]
_native_module = sys.modules.get("pf_native_control")
if _native_module is None:
    _native_path = _native_root / "tools/pf_native_control.py"
    _native_source = _native_path.read_bytes()
    _native_module = type(sys)("pf_native_control")
    _native_module.__file__ = str(_native_path)
    setattr(_native_module, "_captured_source", _native_source)
    sys.modules["pf_native_control"] = _native_module
    exec(
        compile(_native_source, str(_native_path), "exec", dont_inherit=True),
        _native_module.__dict__,
    )
_captured_native_source = getattr(_native_module, "_captured_source", None)
if not isinstance(_captured_native_source, bytes):
    # A previously imported unsealed library is a supported source-mode caller.
    # It cannot promote itself to a sealed publication via its current-file hash.
    if getattr(_native_module, "_PUBLICATION_SEAL", None) is not None:
        raise getattr(_native_module, "NativeControlError")()
    _native_entry = None
else:
    _native_entry = getattr(_native_module, "bootstrap_entry")(
        _native_root, trusted_leaf=_captured_native_source
    )


if TYPE_CHECKING:
    from processforge_core.executions.model import ProcessIdentity

MAX_MANIFEST_BYTES = 4 * 1024 * 1024
HEARTBEAT_INTERVAL_SECONDS = 2.0


class ExecutorError(Exception):
    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


def _utc_now() -> str:
    return (
        datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    )


def _write_json_atomic(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    os.replace(temporary, path)


def write_heartbeat(
    path: Path, status: str, *, sequence: int, extra: dict[str, Any] | None = None
) -> None:
    payload: dict[str, Any] = {
        "schema_version": 1,
        "status": status,
        "sequence": sequence,
        "updated_at": _utc_now(),
    }
    if extra:
        payload.update(extra)
    _write_json_atomic(path, payload)


def write_exit_contract(path: Path, exit_code: int) -> None:
    # Match codex_exec_worker.write_exit_contract's durable compatibility shape.
    status = "completed" if exit_code == 0 else "failed"
    _write_json_atomic(
        path, {"schema_version": 1, "exit_code": int(exit_code), "status": status}
    )


_LAUNCH_ENV = (
    "PF_EXECUTION_PROJECT_ID",
    "PF_EXECUTION_RUN_ID",
    "PF_EXECUTION_TASK_ID",
    "PF_EXECUTION_ATTEMPT",
    "PF_EXECUTION_LAUNCH_TOKEN",
)


def _kernel() -> Any:
    import ctypes
    from ctypes import wintypes

    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    for name, arguments, result in (
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
        ("TerminateJobObject", (wintypes.HANDLE, wintypes.UINT), wintypes.BOOL),
        ("GetCurrentProcess", (), wintypes.HANDLE),
        ("CloseHandle", (wintypes.HANDLE,), wintypes.BOOL),
    ):
        function = getattr(kernel, name)
        function.argtypes, function.restype = arguments, result
    return kernel


def _create_job(name: str) -> Any:
    """Own this wrapper and all inherited descendants before target creation."""
    import ctypes
    from ctypes import wintypes

    class Limits(ctypes.Structure):
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

    class Extended(ctypes.Structure):
        _fields_ = [
            ("basic", Limits),
            ("io", ctypes.c_uint64 * 6),
            ("memory", ctypes.c_size_t * 4),
        ]

    kernel = _kernel()
    ctypes.set_last_error(0)
    handle = kernel.CreateJobObjectW(None, name)
    if not handle:
        raise ExecutorError("execution_activity_unknown")
    try:
        if ctypes.get_last_error() == 183:
            raise ExecutorError("execution_identity_conflict")
        limits = Extended()
        limits.basic.flags = 0x2000  # KILL_ON_JOB_CLOSE; no breakaway permission.
        if not kernel.SetInformationJobObject(
            handle, 9, ctypes.byref(limits), ctypes.sizeof(limits)
        ):
            raise ExecutorError("execution_activity_unknown")
        if not kernel.AssignProcessToJobObject(handle, kernel.GetCurrentProcess()):
            raise ExecutorError("execution_activity_unknown")
        return handle
    except BaseException:
        kernel.CloseHandle(handle)
        raise


def owned_tree_absent(process: ProcessIdentity) -> bool | None:
    """Query the receipt-bound kernel job/group; never infer tree from PID alone."""
    from processforge_core.runtime.process_identity import probe_process

    root = probe_process(process)
    if root == "unknown" or process.tree_id is None:
        return None
    if os.name == "nt":
        import ctypes
        from ctypes import wintypes

        class Accounting(ctypes.Structure):
            _fields_ = [
                ("times", ctypes.c_int64 * 4),
                ("faults", wintypes.DWORD),
                ("total", wintypes.DWORD),
                ("active", wintypes.DWORD),
                ("terminated", wintypes.DWORD),
            ]

        if not process.tree_id.startswith("windows-job:Local\\pf-execution-"):
            return None
        kernel = _kernel()
        handle = kernel.OpenJobObjectW(4, False, process.tree_id.split(":", 1)[1])
        if not handle:
            return True if root == "absent" and ctypes.get_last_error() == 2 else None
        try:
            accounting = Accounting()
            if not kernel.QueryInformationJobObject(
                handle, 1, ctypes.byref(accounting), ctypes.sizeof(accounting), None
            ):
                return None
            return accounting.active == 0
        finally:
            kernel.CloseHandle(handle)
    if (
        sys.platform.startswith("linux")
        and process.tree_id == f"linux-pgid:{process.pid}"
    ):
        try:
            os.killpg(process.pid, 0)
            return False
        except ProcessLookupError:
            # Escaped descendants are not covered by process-group disappearance.
            return None
        except PermissionError:
            return None
    return None


def signal_owned_tree(process: ProcessIdentity) -> None:
    """Signal only the receipt-bound job or a live exact-root process group."""
    from processforge_core.runtime.process_identity import probe_process

    if probe_process(process) == "unknown":
        raise ExecutorError("execution_activity_unknown")
    if (
        os.name == "nt"
        and process.tree_id
        and process.tree_id.startswith("windows-job:Local\\pf-execution-")
    ):
        kernel = _kernel()
        handle = kernel.OpenJobObjectW(8, False, process.tree_id.split(":", 1)[1])
        if not handle:
            if owned_tree_absent(process) is True:
                return
            raise ExecutorError("execution_activity_unknown")
        try:
            if not kernel.TerminateJobObject(handle, 130):
                raise ExecutorError("execution_activity_unknown")
        finally:
            kernel.CloseHandle(handle)
        return
    if (
        sys.platform.startswith("linux")
        and process.tree_id == f"linux-pgid:{process.pid}"
        and probe_process(process) == "same"
    ):
        import signal

        os.killpg(process.pid, signal.SIGTERM)
        return
    raise ExecutorError("execution_activity_unknown")


class ExecutionReceipts:
    """Atomic exact-attempt evidence; only the outermost wrapper owns receipts."""

    def __init__(
        self,
        environment: dict[str, str],
        document: dict[str, Any],
        heartbeat: Path,
        exit_path: Path,
    ):
        from dataclasses import asdict

        from processforge_core.executions.model import ExecutionKey
        from processforge_core.runtime.process_identity import capture_process

        self.identity: dict[str, Any] = {}
        self.process: dict[str, Any] = {}
        self.sequence: dict[str, int] = {}
        self.job: Any = None
        self.heartbeat, self.exit_path = heartbeat, exit_path
        if not any(name in environment for name in _LAUNCH_ENV):
            return
        identity = document["identity"]
        values = tuple(environment.get(name, "") for name in _LAUNCH_ENV)
        if values[:4] != (
            identity["project_id"],
            identity["run_id"],
            identity["assignment_id"],
            str(identity["attempt"]),
        ):
            raise ExecutorError("execution_identity_conflict")
        if len(values[4]) != 32 or any(c not in "0123456789abcdef" for c in values[4]):
            raise ExecutorError("execution_identity_conflict")
        ExecutionKey(values[0], values[1], values[2], int(values[3]))
        self.identity = dict(
            zip(
                ("project_id", "run_id", "task_id", "attempt", "launch_token"),
                values,
                strict=True,
            )
        )
        self.identity["attempt"] = int(values[3])
        if os.name == "nt":
            from pf_native_control import inherited_job

            name = "Local\\pf-execution-" + values[4]
            inherited = inherited_job(environment)
            if inherited is not None:
                if inherited.name != name:
                    raise ExecutorError("execution_identity_conflict")
                self.job = inherited.handle
            else:
                self.job = _create_job(name)
            tree_id = "windows-job:" + name
        elif sys.platform.startswith("linux") and os.getpgrp() == os.getpid():
            tree_id = f"linux-pgid:{os.getpid()}"
        else:
            raise ExecutorError("execution_activity_unknown")
        process = capture_process(os.getpid(), tree_id=tree_id)
        if process is None:
            raise ExecutorError("execution_activity_unknown")
        self.process = asdict(process)
        self.publish(
            heartbeat.with_name("process.json"),
            "process",
            {"pid": os.getpid(), "started_at": _utc_now()},
        )

    def publish(self, path: Path, kind: str, payload: dict[str, Any]) -> None:
        if self.identity:
            payload = {
                **payload,
                "schema_version": 1,
                **self.identity,
                "receipt_kind": kind,
                "sequence": self.sequence.get(kind, 0),
                "observed_at": _utc_now(),
                "process": self.process,
            }
            self.sequence[kind] = payload["sequence"] + 1
            raw = json.dumps(
                payload,
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=False,
                allow_nan=False,
            ).encode("utf-8")
            payload["checksum"] = "sha256:" + hashlib.sha256(raw).hexdigest()
        _write_json_atomic(path, payload)

    def heartbeat_receipt(self, status: str) -> None:
        self.publish(
            self.heartbeat, "heartbeat", {"status": status, "updated_at": _utc_now()}
        )

    def exit_receipt(self, exit_code: int) -> None:
        self.publish(
            self.exit_path,
            "exit",
            {
                "status": "completed" if exit_code == 0 else "failed",
                "exit_code": exit_code,
                "finished_at": _utc_now(),
            },
        )


def _canonical_digest(value: Any) -> bool:
    if (
        not isinstance(value, str)
        or len(value) != 71
        or not value.startswith("sha256:")
    ):
        return False
    return all(char in "0123456789abcdef" for char in value[7:])


def _same_path(left: str, right: str) -> bool:
    try:
        return Path(left).expanduser().resolve() == Path(right).expanduser().resolve()
    except OSError, RuntimeError, ValueError:
        return False


def load_and_validate_manifest(
    args: argparse.Namespace, environ: dict[str, str]
) -> dict[str, Any]:
    supplied_path = str(args.prepared_input)
    env_path = environ.get("PF_PREPARED_INPUT_FILE", "")
    if not env_path or not _same_path(supplied_path, env_path):
        raise ExecutorError("prepared_input_path_mismatch")

    supplied_digest = str(args.prepared_sha256)
    env_digest = environ.get("PF_PREPARED_INPUT_SHA256", "")
    if not _canonical_digest(supplied_digest) or supplied_digest != env_digest:
        raise ExecutorError("prepared_input_digest_pointer_mismatch")

    path = Path(supplied_path).expanduser()
    try:
        with path.open("rb") as stream:
            raw = stream.read(MAX_MANIFEST_BYTES + 1)
    except OSError as exc:
        raise ExecutorError("prepared_input_unreadable") from exc
    if len(raw) > MAX_MANIFEST_BYTES:
        raise ExecutorError("prepared_input_too_large")
    actual_digest = "sha256:" + hashlib.sha256(raw).hexdigest()
    if actual_digest != supplied_digest:
        raise ExecutorError("prepared_input_digest_mismatch")
    try:
        document = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ExecutorError("prepared_input_invalid_json") from exc
    if (
        not isinstance(document, dict)
        or type(document.get("schema_version")) is not int
        or document.get("schema_version") != 1
        or document.get("kind") != "pf.prepared-input"
    ):
        raise ExecutorError("prepared_input_schema_invalid")
    semantic = document.get("input") or {}
    if (
        document.get("egress")
        or isinstance(semantic, dict)
        and (
            semantic.get("egress")
            or semantic.get("contract_version") == 2
            or (semantic.get("execution_contract") or {}).get("contract_version") == 2
        )
    ):
        raise ExecutorError("enforcement_unavailable")

    identity = document.get("identity")
    if not isinstance(identity, dict):
        raise ExecutorError("prepared_input_identity_invalid")
    required_identity = ("project_id", "run_id", "assignment_id", "context_id")
    if any(
        not isinstance(identity.get(key), str) or not identity[key].strip()
        for key in required_identity
    ):
        raise ExecutorError("prepared_input_identity_invalid")
    attempt_value = identity.get("attempt")
    if (
        isinstance(attempt_value, bool)
        or not isinstance(attempt_value, (str, int))
        or str(attempt_value).strip() == ""
    ):
        raise ExecutorError("prepared_input_identity_invalid")
    expected_environment = {
        "run_id": "PF_WORKER_RUN_ID",
        "assignment_id": "PF_WORKER_TASK_ID",
        "attempt": "PF_WORKER_ATTEMPT",
    }
    for field, variable in expected_environment.items():
        expected = environ.get(variable, "")
        if not expected or str(identity.get(field)) != expected:
            raise ExecutorError("prepared_input_identity_mismatch")

    project_root = document.get("project_root")
    if not isinstance(project_root, str) or not project_root.strip():
        raise ExecutorError("prepared_input_project_root_invalid")
    env_project_root = environ.get("PF_PROJECT_ROOT")
    if env_project_root and not _same_path(project_root, env_project_root):
        raise ExecutorError("prepared_input_project_root_mismatch")
    return document


def _arguments(argv: Sequence[str]) -> tuple[argparse.Namespace, list[str]]:
    try:
        separator = list(argv).index("--")
    except ValueError as exc:
        raise ExecutorError("target_separator_required") from exc
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prepared-input", required=True)
    parser.add_argument("--prepared-sha256", required=True)
    parser.add_argument("--heartbeat", required=True)
    parser.add_argument("--exit-path", required=True)
    try:
        options = parser.parse_args(list(argv[:separator]))
    except SystemExit as exc:
        raise ExecutorError("wrapper_arguments_invalid") from exc
    target = list(argv[separator + 1 :])
    if not target or not target[0]:
        raise ExecutorError("target_argv_required")
    return options, target


def _write_failure(paths: tuple[Path, Path] | None, code: int, reason: str) -> None:
    if paths is None:
        return
    heartbeat, exit_path = paths
    try:
        write_heartbeat(heartbeat, "failed", sequence=0, extra={"failure_code": reason})
    except OSError, ValueError:
        pass
    try:
        write_exit_contract(exit_path, code)
    except OSError, ValueError:
        pass


def _terminate_and_wait(process: subprocess.Popen[Any]) -> None:
    """Terminate the exact contained target and wait for the whole native set."""
    from pf_native_control import NativeControlError

    job = getattr(process, "native_job", None)
    if job is None or not job.stop(deadline=time.monotonic() + 5):
        raise NativeControlError()
    process.wait(timeout=5)
    job.close()


def run_target(
    options: argparse.Namespace,
    target: list[str],
    environ: dict[str, str] | None = None,
) -> int:
    from pf_native_control import NativeControlError

    try:
        return _run_target_in_operation(options, target, environ=environ)
    except NativeControlError:
        print("FAIL: execution_activity_unknown", file=sys.stderr)
        return 125


def _run_target_in_operation(
    options: argparse.Namespace,
    target: list[str],
    environ: dict[str, str] | None = None,
) -> int:
    from pf_native_control import operation_lease

    with operation_lease():
        current_env = dict(os.environ if environ is None else environ)
        heartbeat = Path(options.heartbeat).expanduser()
        exit_path = Path(options.exit_path).expanduser()
        output_paths = (heartbeat, exit_path)
        try:
            document = load_and_validate_manifest(options, current_env)
            src = str(Path(__file__).resolve().parents[1] / "src")
            if src not in sys.path:
                sys.path.insert(0, src)
            from processforge_core.runtime.command import load_configuration_snapshot

            load_configuration_snapshot(
                document, Path(options.prepared_input), current_env
            )
            if document.get("native_launch", {}).get("maintenance") is not None:
                tools_path = str(_native_root / "tools")
                if tools_path not in sys.path:
                    sys.path.insert(0, tools_path)
                import pf_native_maintenance as maintenance

                maintenance.validate_preparation(
                    document, Path(document["project_root"]), _native_root
                )
                expected = [
                    sys.executable,
                    "-I",
                    "-B",
                    str(_native_root / "tools/pf_native_maintenance.py"),
                    str(Path(options.prepared_input)),
                ]
                if target != expected:
                    raise ExecutorError("fixed_command_mismatch")
        except (ExecutorError, OSError, ValueError) as exc:
            reason = (
                exc.code
                if isinstance(exc, ExecutorError)
                else "configuration_snapshot_invalid"
            )
            _write_failure(output_paths, 125, reason)
            print(f"FAIL: {reason}", file=sys.stderr)
            return 125

        receipts = None
        if any(name in current_env for name in _LAUNCH_ENV):
            try:
                receipts = ExecutionReceipts(
                    current_env, document, heartbeat, exit_path
                )
            except ExecutorError, OSError, ValueError:
                print("FAIL: execution_activity_unknown", file=sys.stderr)
                return 125
        child_environment = dict(current_env)
        if receipts is not None:
            # A nested Codex wrapper is part of this owned tree, not another writer.
            for name in _LAUNCH_ENV:
                child_environment.pop(name, None)
        started_at = _utc_now()
        try:
            if receipts is None:
                write_heartbeat(
                    heartbeat, "starting", sequence=0, extra={"started_at": started_at}
                )
            else:
                receipts.heartbeat_receipt("starting")
            from pf_native_control import spawn_owned

            process = spawn_owned(
                target,
                shell=False,
                stdin=None,
                stdout=None,
                stderr=None,
                cwd=None,
                env=child_environment,
            )
        except Exception:
            if receipts is None:
                _write_failure(output_paths, 127, "target_launch_failed")
            else:
                receipts.exit_receipt(127)
            print("FAIL: target_launch_failed", file=sys.stderr)
            return 127
        sequence = 0
        next_heartbeat = time.monotonic() + HEARTBEAT_INTERVAL_SECONDS
        try:
            while process.poll() is None:
                remaining = next_heartbeat - time.monotonic()
                if remaining > 0:
                    time.sleep(min(remaining, HEARTBEAT_INTERVAL_SECONDS))
                if time.monotonic() >= next_heartbeat and process.poll() is None:
                    sequence += 1
                    if receipts is None:
                        write_heartbeat(
                            heartbeat,
                            "running",
                            sequence=sequence,
                            extra={"pid": process.pid, "started_at": started_at},
                        )
                    else:
                        receipts.heartbeat_receipt("running")
                    next_heartbeat = time.monotonic() + HEARTBEAT_INTERVAL_SECONDS
            exit_code = int(process.wait())
            job = getattr(process, "native_job", None)
            if job is not None:
                # The target may have returned while its descendants still run.
                while job.active():
                    time.sleep(0.05)
                job.close()
            status = "completed" if exit_code == 0 else "failed"
            if receipts is None:
                write_exit_contract(exit_path, exit_code)
                write_heartbeat(
                    heartbeat,
                    status,
                    sequence=sequence + 1,
                    extra={
                        "pid": process.pid,
                        "exit_code": exit_code,
                        "started_at": started_at,
                        "finished_at": _utc_now(),
                    },
                )
            else:
                receipts.exit_receipt(exit_code)
                receipts.heartbeat_receipt(status)
            return exit_code
        except KeyboardInterrupt:
            _terminate_and_wait(process)
            if receipts is None:
                _write_failure(output_paths, 130, "target_interrupted")
            else:
                receipts.exit_receipt(130)
            return 130
        except Exception:
            _terminate_and_wait(process)
            if receipts is None:
                _write_failure(output_paths, 125, "executor_lifecycle_failed")
            else:
                receipts.exit_receipt(125)
            print("FAIL: executor_lifecycle_failed", file=sys.stderr)
            return 125


def main(argv: Sequence[str] | None = None) -> int:
    raw = list(sys.argv[1:] if argv is None else argv)
    try:
        options, target = _arguments(raw)
    except ExecutorError as exc:
        print(f"FAIL: {exc.code}", file=sys.stderr)
        return 2
    return run_target(options, target)


if __name__ == "__main__":
    raise SystemExit(main())
