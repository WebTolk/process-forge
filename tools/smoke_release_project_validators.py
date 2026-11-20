#!/usr/bin/env python3
"""Run project release gates on a fresh consumer, never on the distribution."""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))

from pf_native_control import spawn_owned  # noqa: E402

STEP_TIMEOUT = 60
CLEANUP_TIMEOUT = 10


_LINUX_STEP = r"""
import os, subprocess, sys
with os.fdopen(int(sys.argv[1]), "w", encoding="ascii") as report:
    try:
        result = subprocess.call(sys.argv[2:], close_fds=True)
    except OSError as error:
        report.write("E" + str(error.errno or 0) + "\n")
    else:
        report.write("R" + str(result) + "\n")
"""


def _linux_step_result(descriptor: int, command: list[str]) -> int:
    """Observe the command result before its namespace's remaining descendants."""
    import select

    deadline = time.monotonic() + STEP_TIMEOUT
    raw = bytearray()
    while True:
        remaining = deadline - time.monotonic()
        if remaining <= 0 or not select.select([descriptor], [], [], remaining)[0]:
            raise subprocess.TimeoutExpired(command, STEP_TIMEOUT)
        chunk = os.read(descriptor, 32 - len(raw))
        if not chunk:
            raise RuntimeError("consumer command result unavailable")
        raw.extend(chunk)
        if len(raw) >= 32:
            raise RuntimeError("consumer command result invalid")
        if raw.endswith(b"\n"):
            value = bytes(raw[1:-1])
            digits = value[1:] if value.startswith(b"-") else value
            if not digits or not digits.isdigit():
                raise RuntimeError("consumer command result invalid")
            result = int(value)
            if raw[:1] == b"E":
                raise OSError(result, "consumer command launch failed")
            if raw[:1] != b"R" or not -255 <= result <= 255:
                raise RuntimeError("consumer command result invalid")
            return result


def run_step(root: Path, env: dict[str, str], *args: str) -> None:
    """Preserve the native command's output and fail before dependent steps."""
    command = [sys.executable, str(ROOT / "bin/pf.py"), *args]
    if not sys.platform.startswith("linux") and os.name != "nt":
        raise RuntimeError("consumer process containment unavailable")
    descriptor: int | None = None
    if sys.platform.startswith("linux"):
        descriptor, writer = os.pipe()
        try:
            process = spawn_owned(
                [
                    sys.executable,
                    "-I",
                    "-B",
                    "-c",
                    _LINUX_STEP,
                    str(writer),
                    *command,
                ],
                cwd=root,
                env=env,
                pass_fds=(writer,),
                independent=True,
            )
        except BaseException:
            os.close(descriptor)
            raise
        finally:
            os.close(writer)
    else:
        process = spawn_owned(command, cwd=root, env=env)
    job = getattr(process, "native_job")
    primary: BaseException | None = None
    try:
        result = (
            process.wait(timeout=STEP_TIMEOUT)
            if descriptor is None
            else _linux_step_result(descriptor, command)
        )
        if result:
            raise subprocess.CalledProcessError(result, command)
    except BaseException as error:
        primary = error
        raise
    finally:
        failures: list[Exception] = []
        if descriptor is not None:
            try:
                os.close(descriptor)
            except OSError as error:
                failures.append(error)
        # Stop even after the launcher exits: grandchildren may still own files.
        # Only the retained native ownership object grants termination authority.
        deadline = time.monotonic() + CLEANUP_TIMEOUT
        try:
            if not job.stop(deadline=deadline):
                raise RuntimeError("consumer process tree termination timed out")
            process.wait(timeout=max(0, deadline - time.monotonic()))
        except Exception as error:
            failures.append(error)
        try:
            job.close()
        except Exception as error:
            failures.append(error)
        if failures:
            failure = primary if primary is not None else failures[0]
            # main must retain the fixture when tree exit cannot be proved.
            setattr(failure, "consumer_cleanup_safe", False)
            setattr(failure, "consumer_cleanup_errors", tuple(failures))
            for cleanup_error in failures:
                failure.add_note(
                    "release consumer process cleanup failed: "
                    + type(cleanup_error).__name__
                )
            if primary is None:
                raise failure


def remove_fixture(temporary: str) -> None:
    """Bound Windows sharing-violation retries after confirmed native tree exit."""
    deadline = time.monotonic() + CLEANUP_TIMEOUT
    while True:
        try:
            shutil.rmtree(temporary)
            return
        except OSError as error:
            # Windows may still be releasing terminated processes' file handles.
            # Permission/ACL failures and all unclassified errors are not retried.
            if (
                getattr(error, "winerror", None) not in (32, 33)
                or time.monotonic() >= deadline
            ):
                raise
            time.sleep(min(0.01, max(0, deadline - time.monotonic())))


def prepare_consumer(base: Path, env: dict[str, str]) -> Path:
    """Onboard an isolated file-only consumer and populate its event stream."""
    workplace = base / "workplace"
    project = base / "consumer"
    project.mkdir()
    run_step(
        base,
        env,
        "workplace-init",
        "--workplace",
        str(workplace),
        "--profile",
        "software-development",
        "--apply",
    )
    run_step(
        base,
        env,
        "project-onboard",
        "--project-root",
        str(project),
        "--workplace",
        str(workplace),
        "--type",
        "generic",
        "--process",
        "software-feature-development",
        "--coordination-mode",
        "simple",
        "--apply",
    )
    run_step(
        base,
        env,
        "chat-record",
        "--project-root",
        str(project),
        "--session-id",
        "release-gate",
        "--participant",
        "release-gate",
        "--participant-type",
        "agent",
        "--role",
        "assistant",
        "--content",
        "Release consumer validation",
    )
    transcripts = list((project / ".pf/runtime/chat/transcripts").glob("*.ndjson"))
    if len(transcripts) != 1 or not transcripts[0].read_bytes().strip():
        raise RuntimeError("consumer chat/event fixture was not populated")
    return project


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check", required=True, choices=["events-validate", "doctor-project"]
    )
    args = parser.parse_args(argv)
    # A new fixture per gate keeps --only independent of order or earlier smokes.
    temporary = tempfile.mkdtemp(prefix="pf-release-consumer-")
    primary: BaseException | None = None
    cleanup_safe = True
    result = 0
    try:
        base = Path(temporary).resolve()
        env = {
            key: value
            for key, value in os.environ.items()
            if not key.startswith(("PF_", "GIT_"))
        }
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        for key in (
            "LOCALAPPDATA",
            "XDG_CONFIG_HOME",
            "XDG_DATA_HOME",
            "XDG_CACHE_HOME",
            "TEMP",
            "TMP",
            "TMPDIR",
        ):
            target = base / key.lower()
            target.mkdir()
            env[key] = str(target)
        try:
            project = prepare_consumer(base, env)
            run_step(base, env, args.check, "--project-root", str(project))
        except subprocess.CalledProcessError as error:
            primary = error
            print(
                f"FAIL: release consumer command exited {error.returncode}",
                file=sys.stderr,
            )
            result = error.returncode if error.returncode > 0 else 1
        except (OSError, RuntimeError, subprocess.TimeoutExpired) as error:
            primary = error
            detail = (
                f" after {error.timeout} seconds"
                if isinstance(error, subprocess.TimeoutExpired)
                else ""
            )
            print(
                f"FAIL: release consumer fixture: {type(error).__name__}{detail}",
                file=sys.stderr,
            )
            result = 1
    except BaseException as error:
        primary = error
        raise
    finally:
        cleanup_safe = getattr(primary, "consumer_cleanup_safe", True)
        if cleanup_safe:
            try:
                remove_fixture(temporary)
            except OSError as error:
                if primary is None:
                    primary = error
                    result = 1
                else:
                    setattr(primary, "consumer_fixture_cleanup_error", error)
                    primary.add_note(
                        "release consumer fixture cleanup failed: "
                        + type(error).__name__
                    )
                print(
                    "FAIL: release consumer fixture cleanup: " + type(error).__name__,
                    file=sys.stderr,
                )
        else:
            print(
                "FAIL: release consumer fixture retained; process exit unconfirmed",
                file=sys.stderr,
            )
        for note in getattr(primary, "__notes__", ()):
            print(note, file=sys.stderr)
    if result:
        return result
    print(f"PASS: {args.check} on isolated onboarded consumer")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
