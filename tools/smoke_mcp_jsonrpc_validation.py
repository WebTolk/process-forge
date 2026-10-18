#!/usr/bin/env python3
"""Verify native newline-framed MCP validation and notification silence."""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace

from pf_runtime import mcp_server

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    requests = []
    expected = []

    def case(value, code=None):
        requests.append(json.dumps(value))
        expected.append((value.get("id") if isinstance(value, dict) and not isinstance(value.get("id"), (bool, list, dict)) else None, code))

    requests.append("{bad-json")
    expected.append((None, -32700))
    for value in ([], None, 1, {"jsonrpc": "1.0", "id": 2, "method": "initialize"},
                  {"jsonrpc": "2.0", "id": 3, "method": 4},
                  {"jsonrpc": "2.0", "id": True, "method": "initialize"},
                  {"jsonrpc": "2.0", "id": {}, "method": "initialize"}):
        case(value, -32600)
    for params in ([], None, "bad", 2):
        case({"jsonrpc": "2.0", "id": "params", "method": "tools/call", "params": params}, -32602)
    for arguments in ([], None, "bad", {"limit": True}, {"limit": 101}, {"roles": ["invalid"]}, {"unknown": 1}):
        case({"jsonrpc": "2.0", "id": "args", "method": "tools/call", "params": {"name": "pf.session_chat", "arguments": arguments}}, -32602)
    case({"jsonrpc": "2.0", "id": 4, "method": "tools/call", "params": {"name": "pf.work.start", "arguments": {}}}, -32602)
    for evidence in ([3], [True], [None], [[]]):
        case({"jsonrpc": "2.0", "id": "evidence", "method": "tools/call", "params": {"name": "pf.work.transition", "arguments": {"outcome": "completed", "evidence": evidence}}}, -32602)
    case({"jsonrpc": "2.0", "id": 5, "method": "no-such-method"}, -32601)
    case({"jsonrpc": "2.0", "id": None, "method": "initialize"})
    case({"jsonrpc": "2.0", "id": 6, "method": "initialize", "params": {"capabilities": []}}, -32602)
    for method, params in (("initialize", {}), ("tools/list", {}), ("no-such-method", {}),
                           ("tools/call", {"name": "pf.session_chat", "arguments": {}}),
                           ("tools/call", {"name": "pf.work.start", "arguments": []})):
        requests.append(json.dumps({"jsonrpc": "2.0", "method": method, "params": params}))
    case({"jsonrpc": "2.0", "id": "sentinel", "method": "tools/list"})
    with tempfile.TemporaryDirectory(prefix="pf-mcp-validation-") as raw:
        workplace = Path(raw)
        (workplace / "workplace.yaml").write_text("schema_version: 1\nid: fixture-workplace\n", encoding="utf-8")
        result = subprocess.run([sys.executable, str(ROOT / "tools/pf_runtime/mcp_server.py"), "--workplace", str(workplace)],
                                input="\n".join(requests)+"\n", text=True, capture_output=True, timeout=30, cwd=ROOT)
        assert result.returncode == 0, result.stderr
        responses = [json.loads(line) for line in result.stdout.splitlines()]
        assert len(responses) == len(expected), (responses, expected)
        for response, (request_id, code) in zip(responses, expected):
            assert response["jsonrpc"] == "2.0" and response["id"] == request_id, response
            if code is None:
                assert "result" in response and "error" not in response, response
            else:
                assert response.get("error", {}).get("code") == code, response
        # Supplement the real wire proof with a dispatch counter: invalid
        # mutation arguments must not reach business logic, notifications do.
        calls = []
        original = mcp_server.tool_result
        try:
            mcp_server.tool_result = lambda *args: calls.append(args) or {}
            runtime = SimpleNamespace(core=SimpleNamespace())
            notification = {"jsonrpc": "2.0", "method": "tools/call", "params": {"name": "pf.work.start", "arguments": {"objective": "fixture"}}}
            assert mcp_server.respond(notification, workplace, "", runtime) is None
            assert len(calls) == 1
            notification["params"] = {"name": "pf.work.transition", "arguments": {"outcome": "completed", "evidence": [3]}}
            assert mcp_server.respond(notification, workplace, "", runtime) is None
            assert len(calls) == 1
            notification["params"]["arguments"]["evidence"] = ["attestation", {"kind": "artifact"}]
            assert mcp_server.respond(notification, workplace, "", runtime) is None
            assert len(calls) == 2
            notification["params"] = {"name": "pf.work.start", "arguments": {"objective": False}}
            assert mcp_server.respond(notification, workplace, "", runtime) is None
            assert len(calls) == 2
        finally:
            mcp_server.tool_result = original
    print("PASS: native MCP validates JSON-RPC and tool arguments; notifications stay silent")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
