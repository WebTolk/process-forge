"""Opt-in Codex host registration for the ProcessForge stdio MCP server."""

from __future__ import annotations

import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
from typing import Any, Callable


Runner = Callable[[list[str]], subprocess.CompletedProcess[bytes]]
SERVER_NAME_PATTERN = re.compile(r"^[A-Za-z0-9_.-]+$")


def run_command(argv: list[str]) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(argv, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)


def resolved_root(value: str | Path) -> Path:
    return Path(value).expanduser().resolve()


def expected_transport(
    distribution_root: Path,
    workplace_root: Path,
    *,
    python_executable: str,
) -> dict[str, Any]:
    server = resolved_root(distribution_root) / "tools" / "pf_runtime" / "mcp_server.py"
    if not server.is_file():
        raise SystemExit(f"FAIL: ProcessForge MCP server does not exist: {server}")
    return {
        "type": "stdio",
        "command": python_executable,
        "args": [str(server), "--workplace", str(resolved_root(workplace_root))],
    }


def compatible_python_command(command: str) -> bool:
    return Path(command).name.casefold() in {"python", "python.exe", "py", "py.exe"}


def exact_command_match(expected: str, actual: str) -> bool:
    expected_path = Path(expected).expanduser()
    actual_path = Path(actual).expanduser()
    expected_is_path = expected_path.is_absolute() or len(expected_path.parts) > 1
    actual_is_path = actual_path.is_absolute() or len(actual_path.parts) > 1
    if expected_is_path or actual_is_path:
        if not expected_is_path or not actual_is_path:
            return False
        return str(expected_path.resolve()).casefold() == str(actual_path.resolve()).casefold()
    return expected.casefold() == actual.casefold()


def transport_drift(
    expected: dict[str, Any],
    actual: dict[str, Any],
    *,
    strict_python_command: bool = False,
) -> list[str]:
    drift: list[str] = []
    if actual.get("type") != "stdio":
        drift.append("transport.type")
    expected_command = str(expected.get("command") or "")
    actual_command = str(actual.get("command") or "")
    if strict_python_command:
        command_matches = exact_command_match(expected_command, actual_command)
    else:
        command_matches = compatible_python_command(actual_command)
    if not command_matches:
        drift.append("transport.command")
    expected_args = [str(item) for item in expected["args"]]
    actual_args = [str(item) for item in actual.get("args", [])] if isinstance(actual.get("args"), list) else []
    if len(expected_args) != len(actual_args):
        drift.append("transport.args")
    else:
        for index, (wanted, found) in enumerate(zip(expected_args, actual_args)):
            if index in {0, 2}:
                if str(resolved_root(wanted)).casefold() != str(resolved_root(found)).casefold():
                    drift.append("transport.args")
                    break
            elif wanted != found:
                drift.append("transport.args")
                break
    return drift


def validate_name(name: str) -> str:
    if not SERVER_NAME_PATTERN.fullmatch(name):
        raise SystemExit("FAIL: MCP server name may contain only letters, digits, dot, underscore, and hyphen")
    return name


def codex_executable(value: str | None) -> str:
    executable = value or shutil.which("codex")
    if not executable:
        raise SystemExit("FAIL: Codex CLI is not available on PATH; MCP host registration cannot be managed")
    return executable


def status_payload(
    distribution_root: Path,
    workplace_root: Path,
    *,
    name: str = "processforge",
    python_executable: str = sys.executable,
    codex: str = "codex",
    runner: Runner = run_command,
    strict_python_command: bool = False,
) -> dict[str, Any]:
    name = validate_name(name)
    expected = expected_transport(
        distribution_root,
        workplace_root,
        python_executable=python_executable,
    )
    result = runner([codex, "mcp", "get", name, "--json"])
    if result.returncode != 0:
        return {
            "status": "missing",
            "name": name,
            "owner": "codex-host",
            "system_autostart": False,
            "expected": expected,
        }
    try:
        payload = json.loads(result.stdout.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        return {
            "status": "invalid",
            "name": name,
            "owner": "codex-host",
            "system_autostart": False,
            "expected": expected,
            "error": str(exc),
        }
    actual = payload.get("transport") if isinstance(payload.get("transport"), dict) else {}
    drift = transport_drift(expected, actual, strict_python_command=strict_python_command)
    if payload.get("enabled") is not True:
        drift.append("enabled")
    return {
        "status": "drifted" if drift else "installed",
        "name": name,
        "owner": "codex-host",
        "system_autostart": False,
        "expected": expected,
        "actual": actual,
        "drift": sorted(set(drift)),
        "restart_required": False,
    }


def install_server(
    distribution_root: Path,
    workplace_root: Path,
    *,
    name: str,
    python_executable: str,
    codex: str,
    apply: bool,
    replace: bool = False,
    runner: Runner = run_command,
    strict_python_command: bool = False,
) -> dict[str, Any]:
    status = status_payload(
        distribution_root,
        workplace_root,
        name=name,
        python_executable=python_executable,
        codex=codex,
        runner=runner,
        strict_python_command=strict_python_command,
    )
    if status["status"] == "installed":
        return {**status, "operation": "unchanged", "applied": False}
    if status["status"] in {"drifted", "invalid"} and not replace:
        raise SystemExit("FAIL: Codex MCP registration is drifted; use --replace to overwrite it")
    if not apply:
        return {**status, "operation": "install", "applied": False, "replace_required": status["status"] != "missing"}
    if status["status"] != "missing":
        removed = runner([codex, "mcp", "remove", name])
        if removed.returncode != 0:
            error = removed.stderr.decode(errors="replace").strip()
            raise SystemExit(f"FAIL: could not replace Codex MCP registration: {error}")
    expected = status["expected"]
    result = runner(
        [codex, "mcp", "add", name, "--", python_executable, *[str(item) for item in expected["args"]]]
    )
    if result.returncode != 0:
        error = result.stderr.decode(errors="replace").strip()
        raise SystemExit(f"FAIL: could not add Codex MCP registration: {error}")
    return {
        **status,
        "status": "installed",
        "operation": "install",
        "applied": True,
        "restart_required": True,
    }


def remove_server(
    distribution_root: Path,
    workplace_root: Path,
    *,
    name: str,
    python_executable: str,
    codex: str,
    apply: bool,
    force: bool = False,
    runner: Runner = run_command,
    strict_python_command: bool = False,
) -> dict[str, Any]:
    status = status_payload(
        distribution_root,
        workplace_root,
        name=name,
        python_executable=python_executable,
        codex=codex,
        runner=runner,
        strict_python_command=strict_python_command,
    )
    if status["status"] == "missing":
        return {**status, "operation": "unchanged", "applied": False}
    if status["status"] != "installed" and not force:
        raise SystemExit("FAIL: MCP registration is not an exact ProcessForge match; use --force to remove it")
    if not apply:
        return {**status, "operation": "remove", "applied": False}
    result = runner([codex, "mcp", "remove", name])
    if result.returncode != 0:
        error = result.stderr.decode(errors="replace").strip()
        raise SystemExit(f"FAIL: could not remove Codex MCP registration: {error}")
    return {**status, "status": "missing", "operation": "remove", "applied": True, "restart_required": True}


def distribution_root(args: Any, core: Any) -> Path:
    return resolved_root(getattr(args, "distribution_root", None) or core.ROOT)


def print_payload(payload: dict[str, Any], *, as_json: bool) -> int:
    if as_json:
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(
            f"CODEX MCP: {payload.get('status')} name={payload.get('name')} "
            f"owner={payload.get('owner')} operation={payload.get('operation', 'status')}"
        )
    return 0 if payload.get("status") != "invalid" else 1


def command_status(args: Any, core: Any) -> int:
    workplace = core.resolve_workplace_root(args.workplace)
    payload = status_payload(
        distribution_root(args, core),
        workplace,
        name=args.name,
        python_executable=args.python or sys.executable,
        codex=codex_executable(args.codex),
        strict_python_command=bool(args.python),
    )
    return print_payload(payload, as_json=args.json)


def command_install(args: Any, core: Any) -> int:
    workplace = core.resolve_workplace_root(args.workplace)
    payload = install_server(
        distribution_root(args, core),
        workplace,
        name=args.name,
        python_executable=args.python or sys.executable,
        codex=codex_executable(args.codex),
        apply=args.apply,
        replace=args.replace,
        strict_python_command=bool(args.python),
    )
    return print_payload(payload, as_json=args.json)


def command_remove(args: Any, core: Any) -> int:
    workplace = core.resolve_workplace_root(args.workplace)
    payload = remove_server(
        distribution_root(args, core),
        workplace,
        name=args.name,
        python_executable=args.python or sys.executable,
        codex=codex_executable(args.codex),
        apply=args.apply,
        force=args.force,
        strict_python_command=bool(args.python),
    )
    return print_payload(payload, as_json=args.json)
