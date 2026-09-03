from __future__ import annotations

import json
from pathlib import Path
import subprocess
import tempfile

from pf_runtime import codex_mcp
from pf_runtime import windows_autostart


def assert_true(value: bool, message: str) -> None:
    if not value:
        raise AssertionError(message)


def completed(argv: list[str], returncode: int = 0, stdout: bytes = b"", stderr: bytes = b"") -> subprocess.CompletedProcess[bytes]:
    return subprocess.CompletedProcess(argv, returncode, stdout=stdout, stderr=stderr)


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="pf-autostart-smoke-") as temp_dir:
        root = Path(temp_dir)
        distribution = root / "distribution"
        workplace = root / "workplace"
        (distribution / "bin").mkdir(parents=True)
        (distribution / "bin" / "pf.py").write_text("# bridge\n", encoding="utf-8")
        (distribution / "tools" / "pf_runtime").mkdir(parents=True)
        (distribution / "tools" / "pf_runtime" / "mcp_server.py").write_text("# mcp\n", encoding="utf-8")
        workplace.mkdir()

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

    print("PASS: Runtime Task Scheduler and Codex MCP lifecycle contracts are stable.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
