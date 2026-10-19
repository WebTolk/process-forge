from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace
from unittest.mock import patch
import xml.etree.ElementTree as ET

from pf_runtime import codex_mcp
from pf_runtime import windows_autostart


def assert_true(value: bool, message: str) -> None:
    if not value:
        raise AssertionError(message)


def completed(argv: list[str], returncode: int = 0, stdout: bytes = b"", stderr: bytes = b"") -> subprocess.CompletedProcess[bytes]:
    return subprocess.CompletedProcess(argv, returncode, stdout=stdout, stderr=stderr)


def check_window_profile(distribution: Path, workplace: Path, root: Path) -> None:
    interpreter_dir = root / "Python spaces \u03a9"
    interpreter_dir.mkdir()
    python = str(interpreter_dir / "python.exe")
    # A nearby pythonw must never override an explicitly selected interpreter.
    for name in ("python.exe", "pythonw.exe"):
        (interpreter_dir / name).write_text("# fixture only\n", encoding="utf-8")
    argv = [str(distribution.resolve() / "tools" / "processforge.py"), "runtime", "serve", "--minimized",
            "--workplace", str(workplace.resolve()), "--port", "9876", "--interval", "3.5"]
    action = windows_autostart.runtime_action(distribution, workplace, python_executable=python, port=9876, interval=3.5)
    assert_true(action["command"] == python, "explicit Python was replaced")
    assert_true(action["arguments"] == subprocess.list2cmdline(argv), "foreground minimized action argv changed")
    assert_true(action["working_directory"] == str(distribution.resolve()), "task working directory changed")
    if sys.platform == "win32":
        import ctypes
        from ctypes import wintypes
        shell = ctypes.WinDLL("shell32", use_last_error=True)
        kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        shell.CommandLineToArgvW.argtypes = [wintypes.LPCWSTR, ctypes.POINTER(ctypes.c_int)]
        shell.CommandLineToArgvW.restype = ctypes.POINTER(wintypes.LPWSTR)
        kernel.LocalFree.argtypes = [ctypes.c_void_p]
        kernel.LocalFree.restype = ctypes.c_void_p
        count = ctypes.c_int()
        parsed = shell.CommandLineToArgvW(subprocess.list2cmdline([python, *argv]), ctypes.byref(count))
        assert_true(bool(parsed), "native argv decoder failed")
        try:
            assert_true([parsed[index] for index in range(count.value)] == [python, *argv], "Windows quoting lost spaces or Unicode")
        finally:
            kernel.LocalFree(parsed)
    xml = windows_autostart.build_task_xml(action, user_id="DOMAIN\\user")
    assert_true(windows_autostart.action_from_xml(xml) == action, "pinned minimized action XML round trip failed")
    node = ET.fromstring(xml)
    ns = {"t": windows_autostart.TASK_NS}
    for path, expected in (("t:Settings/t:Hidden", "false"), ("t:Settings/t:MultipleInstancesPolicy", "IgnoreNew"),
                           ("t:Settings/t:ExecutionTimeLimit", "PT0S"), ("t:Principals/t:Principal/t:LogonType", "InteractiveToken")):
        assert_true(node.findtext(path, namespaces=ns) == expected, f"scheduled task setting changed: {path}")
    common = dict(python_executable=python, port=9876, interval=3.5, platform_name="nt")
    calls = []
    def query_only(argv):
        calls.append(argv)
        assert_true(argv[:2] == ["schtasks.exe", "/Query"], "preview attempted a scheduler mutation")
        return completed(argv, stdout=xml)
    with patch.object(subprocess, "run", side_effect=AssertionError("real scheduler or Codex process must not execute")):
        match = windows_autostart.install_task(distribution, workplace, apply=True, runner=query_only, **common)
        assert_true(match["operation"] == "unchanged" and not match["applied"], "matching action was reapplied")
        preview = windows_autostart.remove_task(distribution, workplace, apply=False, runner=query_only, **common)
        assert_true(preview["operation"] == "remove" and not preview["applied"], "remove preview changed a task")
        for changed in ({**action, "arguments": action["arguments"].replace(" --minimized", "")},
                        {**action, "command": python.replace("python.exe", "pythonw.exe")},
                        {**action, "command": "python.exe"}):
            drift_xml = windows_autostart.build_task_xml(changed, user_id="DOMAIN\\user")
            def drift_runner(argv):
                calls.append(argv)
                assert_true(argv[:2] == ["schtasks.exe", "/Query"], "drift refusal attempted scheduler mutation")
                return completed(argv, stdout=drift_xml)
            drift = windows_autostart.status_payload(distribution, workplace, runner=drift_runner, **common)
            assert_true(drift["status"] == "drifted", "old/minimized/interpreter action drift was accepted")
            try:
                windows_autostart.install_task(distribution, workplace, apply=True, runner=drift_runner, **common)
            except SystemExit as exc:
                assert_true("--replace" in str(exc), "drift refusal did not require explicit replacement")
            else:
                raise AssertionError("drifted task overwritten without --replace")
            planned = windows_autostart.install_task(distribution, workplace, apply=False, replace=True, runner=drift_runner, **common)
            assert_true(not planned["applied"] and planned["replace_required"], "replacement preview changed scheduler")
        unsupported = windows_autostart.status_payload(distribution, workplace, runner=query_only, **{**common, "platform_name": "posix"})
        assert_true(unsupported["status"] == "unsupported", "non-Windows scheduler profile was accepted")
    assert_true(len(calls) == 11, "unexpected scheduler query count")
    for supplied in (python, None):
        args = SimpleNamespace(workplace=str(workplace), distribution_root=str(distribution), python=supplied,
                               apply=False, replace=False, delay_seconds=10, port=9876, interval=3.5, json=True)
        core = SimpleNamespace(resolve_workplace_root=lambda path: workplace)
        with patch.object(windows_autostart, "install_task", return_value={}) as install, patch.object(windows_autostart, "print_payload", return_value=0):
            assert_true(windows_autostart.command_install(args, core) == 0, "CLI install preview failed")
        assert_true(install.call_args.kwargs["python_executable"] == (supplied or sys.executable), "CLI changed the selected interpreter")
    legacy = root / "legacy distribution"
    (legacy / "bin").mkdir(parents=True)
    (legacy / "bin/pf.py").write_text("# old launcher only\n", encoding="utf-8")
    try:
        windows_autostart.runtime_action(legacy, workplace, python_executable=python)
    except SystemExit as exc:
        assert_true("entrypoint does not exist" in str(exc), "missing direct entrypoint error changed")
    else:
        raise AssertionError("old bridge-only distribution silently accepted")


def main() -> int:
    with patch.object(subprocess, "run", side_effect=AssertionError("real scheduler or Codex process must not execute")), tempfile.TemporaryDirectory(prefix="pf-autostart-smoke-") as temp_dir:
        root = Path(temp_dir)
        distribution = root / "distribution spaces \u03a9"
        workplace = root / "workplace spaces \u03a9"
        (distribution / "bin").mkdir(parents=True)
        (distribution / "bin" / "pf.py").write_text("# bridge\n", encoding="utf-8")
        (distribution / "tools" / "pf_runtime").mkdir(parents=True)
        (distribution / "tools" / "pf_runtime" / "mcp_server.py").write_text("# mcp\n", encoding="utf-8")
        (distribution / "tools" / "processforge.py").write_text("# direct CLI fixture\n", encoding="utf-8")
        workplace.mkdir()
        check_window_profile(distribution, workplace, root)

        action = windows_autostart.runtime_action(
            distribution, workplace, python_executable="python.exe", port=0, interval=2.0
        )
        xml = windows_autostart.build_task_xml(action, user_id="DOMAIN\\user", delay_seconds=10)
        assert_true(windows_autostart.action_from_xml(xml) == action, "scheduled task action round trip failed")
        console_xml = xml.decode("utf-16").encode("utf-8")
        assert_true(
            windows_autostart.action_from_xml(console_xml) == action,
            "Task Scheduler console XML declaration mismatch was not normalized",
        )
        assert_true(
            windows_autostart.task_name(workplace) == windows_autostart.task_name(workplace),
            "task name is not deterministic",
        )
        assert_true(
            windows_autostart.task_name(workplace) != windows_autostart.task_name(root / "other-workplace"),
            "workplace-specific task names collided",
        )

        def task_runner(argv: list[str]) -> subprocess.CompletedProcess[bytes]:
            if "/Query" in argv:
                return completed(argv, stdout=xml)
            return completed(argv)

        runtime_status = windows_autostart.status_payload(
            distribution,
            workplace,
            python_executable="python.exe",
            runner=task_runner,
            platform_name="nt",
        )
        assert_true(runtime_status["status"] == "installed", "matching scheduled task was not accepted")
        drifted_xml = windows_autostart.build_task_xml(
            {**action, "arguments": action["arguments"] + " --unexpected"},
            user_id="DOMAIN\\user",
        )
        drifted = windows_autostart.status_payload(
            distribution,
            workplace,
            python_executable="python.exe",
            runner=lambda argv: completed(argv, stdout=drifted_xml),
            platform_name="nt",
        )
        assert_true(drifted["status"] == "drifted" and "arguments" in drifted["drift"], "task drift was not detected")

        expected = codex_mcp.expected_transport(distribution, workplace, python_executable="python.exe")
        codex_payload = {
            "name": "processforge",
            "enabled": True,
            "transport": {**expected, "command": "python"},
        }

        def codex_runner(argv: list[str]) -> subprocess.CompletedProcess[bytes]:
            return completed(argv, stdout=json.dumps(codex_payload).encode("utf-8"))

        mcp_status = codex_mcp.status_payload(
            distribution,
            workplace,
            python_executable="python.exe",
            codex="codex",
            runner=codex_runner,
        )
        assert_true(mcp_status["status"] == "installed", "matching Codex MCP registration was not accepted")
        pinned_python = str(root / "trusted-python.exe")
        pinned_drift = codex_mcp.status_payload(
            distribution,
            workplace,
            python_executable=pinned_python,
            codex="codex",
            runner=codex_runner,
            strict_python_command=True,
        )
        assert_true(
            pinned_drift["status"] == "drifted" and "transport.command" in pinned_drift["drift"],
            "explicit Codex MCP Python command drift was not detected",
        )
        pinned_payload = {
            **codex_payload,
            "transport": {**codex_payload["transport"], "command": pinned_python},
        }
        pinned_match = codex_mcp.status_payload(
            distribution,
            workplace,
            python_executable=pinned_python,
            codex="codex",
            runner=lambda argv: completed(argv, stdout=json.dumps(pinned_payload).encode("utf-8")),
            strict_python_command=True,
        )
        assert_true(pinned_match["status"] == "installed", "exact pinned Codex MCP Python command was rejected")
        wrong = dict(codex_payload)
        wrong["transport"] = {**codex_payload["transport"], "args": [expected["args"][0], "--workplace", str(root / "other")]}
        mcp_drift = codex_mcp.status_payload(
            distribution,
            workplace,
            python_executable="python.exe",
            codex="codex",
            runner=lambda argv: completed(argv, stdout=json.dumps(wrong).encode("utf-8")),
        )
        assert_true(mcp_drift["status"] == "drifted", "Codex MCP workplace drift was not detected")

    print("PASS: Runtime Task Scheduler minimized/exact-interpreter/refusal previews and Codex MCP contracts (no real scheduler changes).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
