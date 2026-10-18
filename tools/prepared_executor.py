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
from typing import Any, Sequence

MAX_MANIFEST_BYTES = 4 * 1024 * 1024
HEARTBEAT_INTERVAL_SECONDS = 2.0


class ExecutorError(Exception):
    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _write_json_atomic(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def write_heartbeat(path: Path, status: str, *, sequence: int, extra: dict[str, Any] | None = None) -> None:
    payload: dict[str, Any] = {"schema_version": 1, "status": status, "sequence": sequence, "updated_at": _utc_now()}
    if extra:
        payload.update(extra)
    _write_json_atomic(path, payload)


def write_exit_contract(path: Path, exit_code: int) -> None:
    # Match codex_exec_worker.write_exit_contract's durable compatibility shape.
    status = "completed" if exit_code == 0 else "failed"
    _write_json_atomic(path, {"schema_version": 1, "exit_code": int(exit_code), "status": status})


def _canonical_digest(value: Any) -> bool:
    if not isinstance(value, str) or len(value) != 71 or not value.startswith("sha256:"):
        return False
    return all(char in "0123456789abcdef" for char in value[7:])


def _same_path(left: str, right: str) -> bool:
    try:
        return Path(left).expanduser().resolve() == Path(right).expanduser().resolve()
    except (OSError, RuntimeError, ValueError):
        return False


def load_and_validate_manifest(args: argparse.Namespace, environ: dict[str, str]) -> dict[str, Any]:
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
    if (not isinstance(document, dict) or type(document.get("schema_version")) is not int
            or document.get("schema_version") != 1 or document.get("kind") != "pf.prepared-input"):
        raise ExecutorError("prepared_input_schema_invalid")
    semantic = document.get("input") or {}
    if (document.get("egress") or isinstance(semantic, dict) and
            (semantic.get("egress") or semantic.get("contract_version") == 2
             or (semantic.get("execution_contract") or {}).get("contract_version") == 2)):
        raise ExecutorError("enforcement_unavailable")

    identity = document.get("identity")
    if not isinstance(identity, dict):
        raise ExecutorError("prepared_input_identity_invalid")
    required_identity = ("project_id", "run_id", "assignment_id", "context_id")
    if any(not isinstance(identity.get(key), str) or not identity[key].strip() for key in required_identity):
        raise ExecutorError("prepared_input_identity_invalid")
    attempt_value = identity.get("attempt")
    if isinstance(attempt_value, bool) or not isinstance(attempt_value, (str, int)) or str(attempt_value).strip() == "":
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
    except (OSError, ValueError):
        pass
    try:
        write_exit_contract(exit_path, code)
    except (OSError, ValueError):
        pass


def _terminate_and_wait(process: subprocess.Popen[Any]) -> None:
    if process.poll() is None:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()


def run_target(options: argparse.Namespace, target: list[str], environ: dict[str, str] | None = None) -> int:
    current_env = dict(os.environ if environ is None else environ)
    heartbeat = Path(options.heartbeat).expanduser()
    exit_path = Path(options.exit_path).expanduser()
    output_paths = (heartbeat, exit_path)
    try:
        load_and_validate_manifest(options, current_env)
    except ExecutorError as exc:
        _write_failure(output_paths, 125, exc.code)
        print(f"FAIL: {exc.code}", file=sys.stderr)
        return 125

    started_at = _utc_now()
    try:
        write_heartbeat(heartbeat, "starting", sequence=0, extra={"started_at": started_at})
        process = subprocess.Popen(target, shell=False, stdin=None, stdout=None, stderr=None, cwd=None, env=current_env)
    except Exception:
        _write_failure(output_paths, 127, "target_launch_failed")
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
                write_heartbeat(heartbeat, "running", sequence=sequence, extra={"pid": process.pid, "started_at": started_at})
                next_heartbeat = time.monotonic() + HEARTBEAT_INTERVAL_SECONDS
        exit_code = int(process.wait())
        status = "completed" if exit_code == 0 else "failed"
        write_exit_contract(exit_path, exit_code)
        write_heartbeat(heartbeat, status, sequence=sequence + 1, extra={"pid": process.pid, "exit_code": exit_code, "started_at": started_at, "finished_at": _utc_now()})
        return exit_code
    except KeyboardInterrupt:
        _terminate_and_wait(process)
        _write_failure(output_paths, 130, "target_interrupted")
        return 130
    except Exception:
        _terminate_and_wait(process)
        _write_failure(output_paths, 125, "executor_lifecycle_failed")
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
