#!/usr/bin/env python3
"""Subprocess helpers with timeout and process-tree cleanup."""

from __future__ import annotations

import os
import signal
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


@dataclass
class CommandResult:
    args: list[str]
    cwd: str | None
    returncode: int | None
    stdout: str
    stderr: str
    timed_out: bool
    timeout_seconds: int | float | None
    label: str | None = None


def tail_text(text: str, max_chars: int = 4000) -> str:
    if len(text) <= max_chars:
        return text
    return text[-max_chars:]


def format_command(args: list[str]) -> str:
    return " ".join(str(item) for item in args)


def _decode_output(value: str | bytes | None) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    return value.decode(errors="replace")


def _taskkill_tree(pid: int) -> None:
    taskkill = "taskkill.exe"
    flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    try:
        killer = subprocess.Popen(
            [taskkill, "/PID", str(pid), "/T", "/F"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            creationflags=flags,
        )
        try:
            killer.communicate(timeout=5)
        except subprocess.TimeoutExpired:
            killer.kill()
            with contextlib_suppress_timeout():
                killer.communicate(timeout=1)
    except OSError:
        return


class contextlib_suppress_timeout:
    def __enter__(self) -> None:
        return None

    def __exit__(self, exc_type: object, exc: object, tb: object) -> bool:
        return exc_type is subprocess.TimeoutExpired


def _terminate_process_tree(proc: subprocess.Popen[str]) -> None:
    if proc.poll() is not None:
        return
    if os.name == "nt":
        _taskkill_tree(proc.pid)
        if proc.poll() is None:
            with contextlib_suppress_timeout():
                proc.terminate()
                proc.wait(timeout=2)
        if proc.poll() is None:
            with contextlib_suppress_timeout():
                proc.kill()
                proc.wait(timeout=2)
        return
    try:
        os.killpg(proc.pid, signal.SIGTERM)
    except ProcessLookupError:
        return
    except OSError:
        with contextlib_suppress_timeout():
            proc.terminate()
            proc.wait(timeout=2)
        return
    with contextlib_suppress_timeout():
        proc.wait(timeout=2)
    if proc.poll() is None:
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except ProcessLookupError:
            return
        except OSError:
            with contextlib_suppress_timeout():
                proc.kill()
                proc.wait(timeout=2)


def run_command(
    args: list[str],
    cwd: str | Path | None = None,
    timeout: int | float = 60,
    env: dict[str, str] | None = None,
    label: str | None = None,
    check: bool = False,
    verbose: bool = False,
) -> CommandResult:
    cwd_text = str(Path(cwd).resolve()) if cwd is not None else None
    command = [str(item) for item in args]
    child_env = dict(env) if env is not None else os.environ.copy()
    child_env.setdefault("PYTHONUNBUFFERED", "1")
    if label or verbose:
        print(f"RUN {label or format_command(command)}:", flush=True)
        print(f"  {format_command(command)}", flush=True)
    creationflags = 0
    if os.name == "nt":
        creationflags = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
    proc = subprocess.Popen(
        command,
        cwd=cwd_text,
        env=child_env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        shell=False,
        start_new_session=(os.name != "nt"),
        creationflags=creationflags,
    )
    timed_out = False
    try:
        stdout, stderr = proc.communicate(timeout=timeout)
    except subprocess.TimeoutExpired as exc:
        timed_out = True
        stdout = _decode_output(exc.stdout)
        stderr = _decode_output(exc.stderr)
        _terminate_process_tree(proc)
        try:
            more_stdout, more_stderr = proc.communicate(timeout=5)
            stdout += _decode_output(more_stdout)
            stderr += _decode_output(more_stderr)
        except subprocess.TimeoutExpired as final_exc:
            stdout += _decode_output(final_exc.stdout)
            stderr += _decode_output(final_exc.stderr)
    result = CommandResult(
        args=command,
        cwd=cwd_text,
        returncode=proc.returncode,
        stdout=stdout or "",
        stderr=stderr or "",
        timed_out=timed_out,
        timeout_seconds=timeout,
        label=label,
    )
    if check and (result.timed_out or result.returncode != 0):
        raise RuntimeError(diagnostic_text(result))
    return result


def diagnostic_text(result: CommandResult, max_chars: int = 4000) -> str:
    lines = [
        "Command:",
        f"  {format_command(result.args)}",
        "",
        "CWD:",
        f"  {result.cwd or os.getcwd()}",
        "",
        "Timeout:",
        f"  {result.timeout_seconds}s",
    ]
    if result.returncode is not None:
        lines.extend(["", "Exit code:", f"  {result.returncode}"])
    if result.stdout:
        lines.extend(["", "STDOUT tail:", tail_text(result.stdout, max_chars)])
    if result.stderr:
        lines.extend(["", "STDERR tail:", tail_text(result.stderr, max_chars)])
    return "\n".join(lines)


__all__ = ["CommandResult", "diagnostic_text", "format_command", "run_command", "tail_text"]
