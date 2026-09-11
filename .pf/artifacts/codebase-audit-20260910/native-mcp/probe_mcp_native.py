#!/usr/bin/env python3
"""Isolated probes for the native PF stdio MCP facade.

The fixture lives in the system temporary directory and is removed on exit.
Only this probe and its captured result are durable audit artifacts.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]
CLI = ROOT / "tools" / "processforge.py"
MCP = ROOT / "tools" / "pf_runtime" / "mcp_server.py"


def run_cli(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(CLI), *args],
        cwd=ROOT,
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        check=False,
    )


def run_mcp(workplace: Path, requests: list[dict[str, object]], *, session: str = "") -> list[dict[str, object]]:
    input_text = "\n".join(json.dumps(item, ensure_ascii=False) for item in requests) + "\n"
    completed = subprocess.run(
        [sys.executable, str(MCP), "--workplace", str(workplace), *( ["--session", session] if session else [])],
        cwd=ROOT,
        input=input_text,
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        check=False,
    )
    if completed.returncode != 0:
        raise AssertionError(f"MCP exited {completed.returncode}: {completed.stderr}")
    return [json.loads(line) for line in completed.stdout.splitlines() if line.strip()]


def summarize_tool_response(response: dict[str, object]) -> dict[str, object]:
    summary: dict[str, object] = {
        "id": response.get("id"),
        "jsonrpc": response.get("jsonrpc"),
    }
    result = response.get("result")
    if isinstance(result, dict):
        summary["isError"] = result.get("isError", False)
        content = result.get("content")
        if isinstance(content, list) and content and isinstance(content[0], dict):
            text = content[0].get("text")
            if isinstance(text, str):
                try:
                    nested = json.loads(text)
                except json.JSONDecodeError:
                    nested = None
                if isinstance(nested, dict) and isinstance(nested.get("error"), dict):
                    summary["tool_error_code"] = nested["error"].get("code")
    if isinstance(response.get("error"), dict):
        summary["jsonrpc_error_code"] = response["error"].get("code")
    return summary


def check_case_session_binding(root: Path) -> dict[str, object]:
    workplace = root / "workplace"
    project = root / "project"
    workplace.mkdir()
    project.mkdir()
    (project / "README.md").write_text("# probe\n", encoding="utf-8")
    for args in (
        ("workplace-init", "--workplace", str(workplace), "--apply"),
        (
            "project-onboard",
            "--project-root",
            str(project),
            "--workplace",
            str(workplace),
            "--type",
            "generic-software-project",
            "--apply",
        ),
        (
            "agent-checkin",
            "--workplace",
            str(workplace),
            "--project-root",
            str(project),
            "--agent",
            "codex",
            "--session",
            "Case-Session",
        ),
    ):
        result = run_cli(*args)
        if result.returncode != 0:
            raise AssertionError(f"CLI failed: {args}\n{result.stdout}\n{result.stderr}")
    exact_responses = run_mcp(
        workplace,
        [
            {"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {"name": "pf.session_context", "arguments": {}}},
        ],
        session="Case-Session",
    )
    second_checkin = run_cli(
        "agent-checkin",
        "--workplace",
        str(workplace),
        "--project-root",
        str(project),
        "--agent",
        "codex",
        "--session",
        "case-session",
    )
    if second_checkin.returncode != 0:
        raise AssertionError(f"CLI collision check-in failed: {second_checkin.stdout}\n{second_checkin.stderr}")
    presence_files = sorted((workplace / "runtime" / "agent-presence").glob("*/*.json"))
    presence_ids = [json.loads(path.read_text(encoding="utf-8")).get("session_id") for path in presence_files]
    collision_upper = run_mcp(
        workplace,
        [{"jsonrpc": "2.0", "id": 2, "method": "tools/call", "params": {"name": "pf.session_context", "arguments": {}}}],
        session="Case-Session",
    )
    collision_lower = run_mcp(
        workplace,
        [{"jsonrpc": "2.0", "id": 3, "method": "tools/call", "params": {"name": "pf.session_context", "arguments": {}}}],
        session="case-session",
    )
    return {
        "case": "case-sensitive session id",
        "expected": "exact opaque ids accepted by agent-checkin remain independently routable",
        "single_checkin": {
            "request_session": "Case-Session",
            "expected": "successful pf.session_context",
            "actual": summarize_tool_response(exact_responses[0]),
        },
        "collision_checkins": {
            "requested_sessions": ["Case-Session", "case-session"],
            "expected_presence_count": 2,
            "actual_presence_count": len(presence_files),
            "actual_presence_session_ids": presence_ids,
            "upper_lookup": summarize_tool_response(collision_upper[0]),
            "lower_lookup": summarize_tool_response(collision_lower[0]),
        },
    }


def check_case_jsonrpc_envelope(root: Path) -> dict[str, object]:
    workplace = root / "workplace-envelope"
    project = root / "project-envelope"
    workplace.mkdir()
    project.mkdir()
    (project / "README.md").write_text("# envelope probe\n", encoding="utf-8")
    for args in (
        ("workplace-init", "--workplace", str(workplace), "--apply"),
        (
            "project-onboard",
            "--project-root",
            str(project),
            "--workplace",
            str(workplace),
            "--type",
            "generic-software-project",
            "--apply",
        ),
    ):
        result = run_cli(*args)
        if result.returncode != 0:
            raise AssertionError(f"CLI failed: {args}\n{result.stdout}\n{result.stderr}")
    cases = [
        {"jsonrpc": "2.0", "method": "tools/list"},
        {"jsonrpc": "2.0", "method": "tools/call", "params": {"name": "pf.context", "arguments": {"project_root": str(project)}}},
        {"jsonrpc": "1.0", "id": 2, "method": "tools/list"},
        {"jsonrpc": "2.0", "id": 3, "method": "tools/call", "params": {"name": "pf.context", "arguments": []}},
    ]
    responses_by_case = [run_mcp(workplace, [case]) for case in cases]

    def compact(response: dict[str, object]) -> dict[str, object]:
        item: dict[str, object] = {"id": response.get("id"), "jsonrpc": response.get("jsonrpc")}
        if isinstance(response.get("error"), dict):
            item["jsonrpc_error_code"] = response["error"].get("code")
        result = response.get("result")
        if isinstance(result, dict):
            item["isError"] = result.get("isError", False)
            content = result.get("content")
            if isinstance(content, list) and content and isinstance(content[0], dict):
                text = content[0].get("text")
                if isinstance(text, str):
                    try:
                        nested = json.loads(text)
                    except json.JSONDecodeError:
                        nested = None
                    if isinstance(nested, dict) and isinstance(nested.get("error"), dict):
                        item["tool_error_code"] = nested["error"].get("code")
                    else:
                        item["content_type"] = content[0].get("type")
        return item

    return {
        "case": "JSON-RPC envelope and params validation",
        "requests": cases,
        "expected": [
            "both valid notifications produce no response",
            "non-2.0 envelope is rejected as invalid request",
            "non-object tools/call arguments are rejected as invalid params",
        ],
        "actual_response_count": sum(len(items) for items in responses_by_case),
        "expected_response_count": 2,
        "actual_response_counts_by_case": [len(items) for items in responses_by_case],
        "expected_response_counts_by_case": [0, 0, 1, 1],
        "actual": [compact(items[0]) if items else {"no_response": True} for items in responses_by_case],
    }


def main() -> int:
    fixture = Path(tempfile.mkdtemp(prefix="pf-native-mcp-"))
    try:
        result = {
            "probe": "native PF stdio MCP",
            "repo_head": run_cli("--version").stdout.strip(),
            "session_binding": check_case_session_binding(fixture),
            "jsonrpc_envelope": check_case_jsonrpc_envelope(fixture),
        }
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
        return 0
    finally:
        shutil.rmtree(fixture, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
