#!/usr/bin/env python3
"""Smoke test the bounded, Codex-compatible ProcessForge MCP contract."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

from context_lock_smoke_helpers import make_project, refresh, run_pf


ROOT = Path(__file__).resolve().parents[1]
SERVER = ROOT / "tools" / "pf_runtime" / "mcp_server.py"


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="pf-mcp-codex-contract-") as raw:
        root = Path(raw)
        project = make_project(root)
        workplace = root / "workplace"
        init = run_pf("workplace-init", "--workplace", str(workplace), "--apply")
        if init.returncode != 0:
            raise AssertionError(init.stdout + init.stderr)
        refresh(project)
        request = "\n".join(
            [
                json.dumps({"jsonrpc": "2.0", "id": 1, "method": "initialize"}),
                json.dumps({"jsonrpc": "2.0", "id": 2, "method": "tools/list"}),
                json.dumps(
                    {
                        "jsonrpc": "2.0",
                        "id": 3,
                        "method": "tools/call",
                        "params": {"name": "pf.context", "arguments": {"project_root": str(project)}},
                    }
                ),
            ]
        ) + "\n"
        result = subprocess.run(
            [sys.executable, str(SERVER), "--workplace", str(workplace)],
            input=request,
            text=True,
            capture_output=True,
            cwd=project,
            timeout=30,
            check=True,
        )
        responses = [json.loads(line) for line in result.stdout.splitlines() if line.strip()]
        tools = {item["name"]: item for item in responses[1]["result"]["tools"]}
        if tools["pf.context"]["annotations"]["readOnlyHint"] is not True:
            raise AssertionError(tools["pf.context"])
        if tools["pf.work.start"]["annotations"]["readOnlyHint"] is not False:
            raise AssertionError(tools["pf.work.start"])
        payload_text = responses[2]["result"]["content"][0]["text"]
        payload = json.loads(payload_text)
        if payload.get("kind") != "pf.context" or payload.get("context", {}).get("status") not in {"fresh", "fresh_with_updates"}:
            raise AssertionError(payload)
        if not isinstance(payload.get("resources", {}).get("authorized_knowledge_ids"), list):
            raise AssertionError(payload.get("resources"))
        if "objective" in payload_text or len(payload_text.encode("utf-8")) > 16384:
            raise AssertionError("pf.context is not a bounded bootstrap projection")
    print("PASS: bounded Codex-compatible PF MCP contract")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
