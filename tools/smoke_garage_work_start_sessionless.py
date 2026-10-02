#!/usr/bin/env python3
"""Smoke test for sessionless pf.work.start."""

from smoke_garage_mode_not_promoted_by_session import MCP, ROOT, call_mcp, cli

import json
import subprocess
import sys
import tempfile
from pathlib import Path

import yaml


def call_mcp_raw(workplace: Path, name: str, arguments: dict[str, object]) -> dict[str, object]:
    request = {"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {"name": name, "arguments": arguments}}
    result = subprocess.run(
        [sys.executable, str(MCP), "--workplace", str(workplace)],
        cwd=ROOT,
        text=True,
        encoding="utf-8",
        input=json.dumps({"jsonrpc": "2.0", "id": 0, "method": "initialize"}) + "\n" + json.dumps(request) + "\n",
        capture_output=True,
        timeout=120,
    )
    if result.returncode != 0:
        raise AssertionError(result.stderr)
    return [json.loads(line) for line in result.stdout.splitlines() if line.strip()][-1]


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="pf-work-start-") as raw:
        root = Path(raw)
        workplace = root / "workplace"
        project = root / "project"
        cli("workplace-init", "--workplace", str(workplace), "--apply")
        cli("project-onboard", "--project-root", str(project), "--workplace", str(workplace), "--type", "generic", "--apply")
        payload = call_mcp(workplace, "pf.work.start", {"project_root": str(project), "objective": "Check project assets"})
        if payload.get("action") != "created_new" or payload.get("session", {}).get("status") != "absent":
            raise AssertionError(payload)
        if not (project / ".pf" / "runs" / str(payload["run_id"]) / "run.yaml").is_file():
            raise AssertionError(payload)
        if not (project / ".pf" / "assignments" / f"{payload['assignment_id']}.yaml").is_file():
            raise AssertionError(payload)
        scope_intent = {"schema_version": 1, "assignment": {
            "allowed_files": ["example.py", ".pf/artifacts/scoped/**"],
            "allowed_read_files": ["example.py"],
            "allowed_actions": ["read", "write_artifact", "write_product"],
            "required_outputs": [{"id": "result", "path": ".pf/artifacts/scoped/result.md"}],
            "expected_report": {"artifact": ".pf/artifacts/scoped/result.md"},
        }}
        scoped = call_mcp(workplace, "pf.work.start", {"project_root": str(project), "objective": "Scoped MCP implementation", "scope_intent": scope_intent})
        if scoped.get("action") != "created_new":
            raise AssertionError(scoped)
        capsule = project / ".pf" / "contexts" / "assignment-capsules" / f"{scoped['assignment_id']}.capsule.yaml"
        data = yaml.safe_load(capsule.read_text(encoding="utf-8"))
        scope = data["execution_contract"]["scope"]
        if "example.py" not in scope["allowed_files"] or "write_product" not in scope["allowed_actions"]:
            raise AssertionError(scope)
        rejected = call_mcp_raw(workplace, "pf.work.start", {"project_root": str(project), "objective": "Bad scoped MCP implementation",
                                                             "scope_intent": {"schema_version": 1, "assignment": {"allowed_actions": ["shell"]}}})
        if rejected.get("error", {}).get("code") != -32602:
            raise AssertionError(rejected)
    print("PASS: sessionless pf.work.start creates governed work with typed scope intent")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
