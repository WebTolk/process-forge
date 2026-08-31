#!/usr/bin/env python3
"""Smoke test for actionable MCP missing-session diagnostics."""

from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from pf_runtime import mcp_server
from pf_runtime.session_read import SessionReadError


def main() -> int:
    payload = json.loads(mcp_server.safe_tool_error(SessionReadError("missing_session")))
    error = payload.get("error") if isinstance(payload.get("error"), dict) else {}
    remediation = error.get("remediation") if isinstance(error.get("remediation"), dict) else {}
    if error.get("code") != "missing_session":
        raise AssertionError(payload)
    if remediation.get("kind") != "ledger_session_required":
        raise AssertionError(payload)
    if remediation.get("repair_actions") != []:
        raise AssertionError(payload)
    if remediation.get("operator_action") != "verify_host_session_integration":
        raise AssertionError(payload)
    checks = remediation.get("checks") if isinstance(remediation.get("checks"), list) else []
    if not any("Garage mode" in str(item) for item in checks):
        raise AssertionError(payload)
    if any("install_codex_hooks" in str(item) for item in checks):
        raise AssertionError(payload)
    schema = mcp_server.tool_schema("pf.project_initialization.repair")
    action = schema.get("properties", {}).get("repair_action", {})
    if "install_codex_hooks" not in action.get("enum", []):
        raise AssertionError(schema)
    print("PASS: MCP missing-session diagnostics are actionable")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
