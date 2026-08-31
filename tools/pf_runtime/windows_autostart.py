"""Windows Task Scheduler integration for the long-lived PF Runtime."""

from __future__ import annotations

import getpass
import hashlib
import json
import locale
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
from typing import Any, Callable
import xml.etree.ElementTree as ET


TASK_NS = "http://schemas.microsoft.com/windows/2004/02/mit/task"
TASK_PREFIX = "ProcessForge Runtime"
Runner = Callable[[list[str]], subprocess.CompletedProcess[bytes]]


def run_command(argv: list[str]) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(argv, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)


def resolved_root(value: str | Path) -> Path:
    return Path(value).expanduser().resolve()


def task_name(workplace_root: Path) -> str:
    identity = str(resolved_root(workplace_root)).replace("\\", "/").casefold()
    suffix = hashlib.sha256(identity.encode("utf-8")).hexdigest()[:12]
    return f"{TASK_PREFIX} {suffix}"


def current_user_id() -> str:
    username = os.environ.get("USERNAME") or getpass.getuser()
    domain = os.environ.get("USERDOMAIN") or ""
    return f"{domain}\\{username}" if domain else username


def runtime_action(
    distribution_root: Path,
    workplace_root: Path,
    *,
    python_executable: str,
    port: int = 0,
    interval: float = 2.0,
) -> dict[str, str]:
    distribution_root = resolved_root(distribution_root)
    workplace_root = resolved_root(workplace_root)
    entrypoint = distribution_root / "bin" / "pf.py"
    if not entrypoint.is_file():
        raise SystemExit(f"FAIL: ProcessForge entrypoint does not exist: {entrypoint}")
    arguments = subprocess.list2cmdline(
        [
            str(entrypoint),
            "runtime",
            "serve",
            "--workplace",
            str(workplace_root),
            "--port",
            str(port),
            "--interval",
            str(interval),
        ]
    )
    return {
        "command": python_executable,
        "arguments": arguments,
        "working_directory": str(distribution_root),
    }


def build_task_xml(action: dict[str, str], *, user_id: str, delay_seconds: int = 10) -> bytes:
    ET.register_namespace("", TASK_NS)
    task = ET.Element(f"{{{TASK_NS}}}Task", {"version": "1.4"})
    registration = ET.SubElement(task, f"{{{TASK_NS}}}RegistrationInfo")
    ET.SubElement(registration, f"{{{TASK_NS}}}Description").text = (
        "Starts the ProcessForge workplace Runtime at interactive user logon."
    )
    triggers = ET.SubElement(task, f"{{{TASK_NS}}}Triggers")
    trigger = ET.SubElement(triggers, f"{{{TASK_NS}}}LogonTrigger")
    ET.SubElement(trigger, f"{{{TASK_NS}}}Enabled").text = "true"
    ET.SubElement(trigger, f"{{{TASK_NS}}}Delay").text = f"PT{max(0, delay_seconds)}S"
    ET.SubElement(trigger, f"{{{TASK_NS}}}UserId").text = user_id
    principals = ET.SubElement(task, f"{{{TASK_NS}}}Principals")
    principal = ET.SubElement(principals, f"{{{TASK_NS}}}Principal", {"id": "Author"})
    ET.SubElement(principal, f"{{{TASK_NS}}}UserId").text = user_id
    ET.SubElement(principal, f"{{{TASK_NS}}}LogonType").text = "InteractiveToken"
    ET.SubElement(principal, f"{{{TASK_NS}}}RunLevel").text = "LeastPrivilege"
    settings = ET.SubElement(task, f"{{{TASK_NS}}}Settings")
    for name, value in (
        ("MultipleInstancesPolicy", "IgnoreNew"),
        ("DisallowStartIfOnBatteries", "false"),
        ("StopIfGoingOnBatteries", "false"),
        ("AllowHardTerminate", "true"),
        ("StartWhenAvailable", "true"),
        ("RunOnlyIfNetworkAvailable", "false"),
        ("Enabled", "true"),
        ("Hidden", "false"),
        ("ExecutionTimeLimit", "PT0S"),
    ):
        ET.SubElement(settings, f"{{{TASK_NS}}}{name}").text = value
    restart = ET.SubElement(settings, f"{{{TASK_NS}}}RestartOnFailure")
    ET.SubElement(restart, f"{{{TASK_NS}}}Interval").text = "PT1M"
    ET.SubElement(restart, f"{{{TASK_NS}}}Count").text = "3"
    actions = ET.SubElement(task, f"{{{TASK_NS}}}Actions", {"Context": "Author"})
    execute = ET.SubElement(actions, f"{{{TASK_NS}}}Exec")
    ET.SubElement(execute, f"{{{TASK_NS}}}Command").text = action["command"]
    ET.SubElement(execute, f"{{{TASK_NS}}}Arguments").text = action["arguments"]
    ET.SubElement(execute, f"{{{TASK_NS}}}WorkingDirectory").text = action["working_directory"]
    return ET.tostring(task, encoding="utf-16", xml_declaration=True)


def normalized_xml_payload(payload: bytes) -> bytes:
    if payload.startswith((b"\xff\xfe", b"\xfe\xff")) or b"\x00" in payload[:80]:
        return payload
    last_error: UnicodeDecodeError | None = None
    encodings = ["utf-8", locale.getpreferredencoding(False), "cp866", "cp1251"]
    for encoding in dict.fromkeys(encodings):
        try:
            text = payload.decode(encoding)
            text = re.sub(r"encoding=(['\"])[^'\"]+\1", 'encoding="utf-8"', text, count=1)
            return text.encode("utf-8")
        except UnicodeDecodeError as exc:
            last_error = exc
    if last_error is not None:
        raise last_error
    return payload


def action_from_xml(payload: bytes) -> dict[str, str]:
    root = ET.fromstring(normalized_xml_payload(payload))
    namespace = {"t": TASK_NS}
    return {
        "command": root.findtext("t:Actions/t:Exec/t:Command", default="", namespaces=namespace),
        "arguments": root.findtext("t:Actions/t:Exec/t:Arguments", default="", namespaces=namespace),
        "working_directory": root.findtext(
            "t:Actions/t:Exec/t:WorkingDirectory", default="", namespaces=namespace
        ),
    }


def comparable_path(value: str) -> str:
    try:
        return str(Path(value).expanduser().resolve()).casefold()
    except (OSError, ValueError):
        return value.casefold()


def action_drift(expected: dict[str, str], actual: dict[str, str]) -> list[str]:
    drift: list[str] = []
    for key in ("command", "working_directory"):
        if comparable_path(expected[key]) != comparable_path(actual.get(key, "")):
            drift.append(key)
    if expected["arguments"] != actual.get("arguments", ""):
        drift.append("arguments")
    return drift


def query_task(name: str, *, runner: Runner = run_command) -> subprocess.CompletedProcess[bytes]:
    return runner(["schtasks.exe", "/Query", "/TN", name, "/XML"])


def status_payload(
    distribution_root: Path,
    workplace_root: Path,
    *,
    python_executable: str,
    port: int = 0,
    interval: float = 2.0,
    runner: Runner = run_command,
    platform_name: str | None = None,
) -> dict[str, Any]:
    platform_name = os.name if platform_name is None else platform_name
    name = task_name(workplace_root)
    expected = runtime_action(
        distribution_root,
        workplace_root,
        python_executable=python_executable,
        port=port,
        interval=interval,
    )
    if platform_name != "nt":
        return {"status": "unsupported", "supported": False, "task_name": name, "expected": expected}
    try:
        result = query_task(name, runner=runner)
    except FileNotFoundError:
        return {"status": "unsupported", "supported": False, "task_name": name, "expected": expected}
    if result.returncode != 0:
        return {"status": "missing", "supported": True, "task_name": name, "expected": expected}
    try:
        actual = action_from_xml(result.stdout)
    except (ET.ParseError, ValueError) as exc:
        return {
            "status": "invalid",
            "supported": True,
            "task_name": name,
            "expected": expected,
            "error": str(exc),
        }
    drift = action_drift(expected, actual)
    return {
        "status": "drifted" if drift else "installed",
        "supported": True,
        "task_name": name,
        "expected": expected,
        "actual": actual,
        "drift": drift,
    }


def install_task(
    distribution_root: Path,
    workplace_root: Path,
    *,
    python_executable: str,
    apply: bool,
    replace: bool = False,
    delay_seconds: int = 10,
    port: int = 0,
    interval: float = 2.0,
    runner: Runner = run_command,
    platform_name: str | None = None,
) -> dict[str, Any]:
    status = status_payload(
        distribution_root,
        workplace_root,
        python_executable=python_executable,
        port=port,
        interval=interval,
        runner=runner,
        platform_name=platform_name,
    )
    if not status.get("supported"):
        raise SystemExit("FAIL: Windows Task Scheduler autostart is available only on Windows")
    if status["status"] == "installed":
        return {**status, "operation": "unchanged", "applied": False}
    if status["status"] in {"drifted", "invalid"} and not replace:
        raise SystemExit("FAIL: ProcessForge Runtime scheduled task is drifted; use --replace to overwrite it")
    if not apply:
        return {**status, "operation": "install", "applied": False, "replace_required": status["status"] != "missing"}
    payload = build_task_xml(status["expected"], user_id=current_user_id(), delay_seconds=delay_seconds)
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(prefix="processforge-runtime-", suffix=".xml", delete=False) as handle:
            handle.write(payload)
            temporary_path = Path(handle.name)
        result = runner(
            ["schtasks.exe", "/Create", "/TN", status["task_name"], "/XML", str(temporary_path), "/F"]
        )
        if result.returncode != 0:
            error = result.stderr.decode(errors="replace").strip()
            raise SystemExit(f"FAIL: could not register ProcessForge Runtime scheduled task: {error}")
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)
    return {**status, "status": "installed", "operation": "install", "applied": True}


def remove_task(
    distribution_root: Path,
    workplace_root: Path,
    *,
    python_executable: str,
    apply: bool,
    force: bool = False,
    port: int = 0,
    interval: float = 2.0,
    runner: Runner = run_command,
    platform_name: str | None = None,
) -> dict[str, Any]:
    status = status_payload(
        distribution_root,
        workplace_root,
        python_executable=python_executable,
        port=port,
        interval=interval,
        runner=runner,
        platform_name=platform_name,
    )
    if not status.get("supported"):
        raise SystemExit("FAIL: Windows Task Scheduler autostart is available only on Windows")
    if status["status"] == "missing":
        return {**status, "operation": "unchanged", "applied": False}
    if status["status"] != "installed" and not force:
        raise SystemExit("FAIL: scheduled task is not an exact ProcessForge match; use --force to remove it")
    if not apply:
        return {**status, "operation": "remove", "applied": False}
    result = runner(["schtasks.exe", "/Delete", "/TN", status["task_name"], "/F"])
    if result.returncode != 0:
        error = result.stderr.decode(errors="replace").strip()
        raise SystemExit(f"FAIL: could not remove ProcessForge Runtime scheduled task: {error}")
    return {**status, "status": "missing", "operation": "remove", "applied": True}


def distribution_root(args: Any, core: Any) -> Path:
    return resolved_root(getattr(args, "distribution_root", None) or core.ROOT)


def print_payload(payload: dict[str, Any], *, as_json: bool) -> int:
    if as_json:
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(
            f"RUNTIME AUTOSTART: {payload.get('status')} task={payload.get('task_name')} "
            f"operation={payload.get('operation', 'status')}"
        )
    return 0 if payload.get("status") not in {"invalid", "unsupported"} else 1


def command_status(args: Any, core: Any) -> int:
    workplace = core.resolve_workplace_root(args.workplace)
    payload = status_payload(
        distribution_root(args, core),
        workplace,
        python_executable=args.python or sys.executable,
        port=args.port,
        interval=args.interval,
    )
    return print_payload(payload, as_json=args.json)


def command_install(args: Any, core: Any) -> int:
    workplace = core.resolve_workplace_root(args.workplace)
    payload = install_task(
        distribution_root(args, core),
        workplace,
        python_executable=args.python or sys.executable,
        apply=args.apply,
        replace=args.replace,
        delay_seconds=args.delay_seconds,
        port=args.port,
        interval=args.interval,
    )
    return print_payload(payload, as_json=args.json)


def command_remove(args: Any, core: Any) -> int:
    workplace = core.resolve_workplace_root(args.workplace)
    payload = remove_task(
        distribution_root(args, core),
        workplace,
        python_executable=args.python or sys.executable,
        apply=args.apply,
        force=args.force,
        port=args.port,
        interval=args.interval,
    )
    return print_payload(payload, as_json=args.json)
