#!/usr/bin/env python3
"""Smoke test the bounded, Codex-compatible ProcessForge MCP contract."""

from __future__ import annotations

import json
import runpy
import subprocess
import sys
import tempfile
from pathlib import Path

import yaml

from context_lock_smoke_helpers import make_project, refresh, run_pf


ROOT = Path(__file__).resolve().parents[1]
SERVER = ROOT / "tools" / "pf_runtime" / "mcp_server.py"
validate_instance = runpy.run_path(str(ROOT / "tools/validate-process-forge-schemas.py"))["validate_instance"]


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="pf-mcp-codex-contract-") as raw:
        root = Path(raw)
        project = make_project(root)
        workplace = root / "workplace"
        init = run_pf("workplace-init", "--workplace", str(workplace), "--apply")
        if init.returncode != 0:
            raise AssertionError(init.stdout + init.stderr)
        refresh(project)
        before_assignments = set((project / ".pf/assignments").glob("*.yaml"))
        mode = {"kind": "assurance", "code_changes_allowed": False,
                "artifact_changes_allowed": True, "requires_review": True}
        starts = []
        for index, representation in enumerate(["assurance", mode, {**mode, "requires_review": "false"}]):
            starts.append({"jsonrpc": "2.0", "id": index + 4, "method": "tools/call", "params": {
                "name": "pf.work.start", "arguments": {"project_root": str(project),
                    "objective": f"MCP assurance representation {index}", "scope_intent": {
                        "schema_version": 1, "assignment": {"execution_mode": representation,
                            "allowed_files": [f".pf/artifacts/mcp-mode-{index}/**"],
                            "allowed_read_files": ["**"], "allowed_actions": ["read", "write_artifact"],
                            "forbidden_actions": ["write_product"]}}}}})
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
            ] + [json.dumps(request) for request in starts]
        ) + "\n"
        result = subprocess.run(
            [sys.executable, str(SERVER), "--workplace", str(workplace)],
            input=request,
            text=True,
            capture_output=True,
            cwd=project,
            timeout=60,
            check=True,
        )
        responses = [json.loads(line) for line in result.stdout.splitlines() if line.strip()]
        tools = {item["name"]: item for item in responses[1]["result"]["tools"]}
        if tools["pf.context"]["annotations"]["readOnlyHint"] is not True:
            raise AssertionError(tools["pf.context"])
        if tools["pf.work.start"]["annotations"]["readOnlyHint"] is not False:
            raise AssertionError(tools["pf.work.start"])
        work_start_schema = tools["pf.work.start"]["inputSchema"]
        scope_schema = work_start_schema.get("properties", {}).get("scope_intent", {})
        assignment_schema = scope_schema.get("properties", {}).get("assignment", {})
        if scope_schema.get("additionalProperties") is not False or assignment_schema.get("additionalProperties") is not False:
            raise AssertionError(scope_schema)
        if "allowed_files" not in assignment_schema.get("properties", {}) or "required_outputs" not in assignment_schema.get("properties", {}):
            raise AssertionError(scope_schema)
        for request in starts[:2]:
            declaration = request["params"]["arguments"]["scope_intent"]
            errors = validate_instance(declaration, scope_schema, scope_schema, "$")
            if errors:
                raise AssertionError(errors)
        invalid = starts[2]["params"]["arguments"]["scope_intent"]
        if not validate_instance(invalid, scope_schema, scope_schema, "$"):
            raise AssertionError("MCP schema accepted a non-boolean mode flag")
        saved_schema = json.loads((ROOT / "schemas/assignment.schema.json").read_text(encoding="utf-8"))
        for response in responses[3:5]:
            started = json.loads(response["result"]["content"][0]["text"])
            if started.get("action") != "created_new":
                raise AssertionError(started)
            state = started["work_state"]
            if state["context"]["validation"]["status"] != "valid" or state["execution_readiness"]["status"] != "ready":
                raise AssertionError(state)
            if "write_product" in state["execution_readiness"]["allowed_actions"]:
                raise AssertionError(state)
            assignment_path = project / ".pf/assignments" / (started["assignment_id"] + ".yaml")
            saved = yaml.safe_load(assignment_path.read_text(encoding="utf-8"))
            errors = validate_instance(saved, saved_schema, saved_schema, "$")
            if errors or saved["execution_mode"] != mode:
                raise AssertionError((errors, saved["execution_mode"]))
        if responses[5].get("error") != {"code": -32602, "message": "invalid params"}:
            raise AssertionError(responses[5])
        if len(set((project / ".pf/assignments").glob("*.yaml")) - before_assignments) != 2:
            raise AssertionError("Malformed mode published an Assignment")
        payload_text = responses[2]["result"]["content"][0]["text"]
        payload = json.loads(payload_text)
        if payload.get("kind") != "pf.context" or payload.get("context", {}).get("status") not in {"fresh", "fresh_with_updates"}:
            raise AssertionError(payload)
        if not isinstance(payload.get("resources", {}).get("authorized_knowledge_ids"), list):
            raise AssertionError(payload.get("resources"))
        if "objective" in payload_text or len(payload_text.encode("utf-8")) > 16384:
            raise AssertionError("pf.context is not a bounded bootstrap projection")
    print("PASS: bounded MCP contract, canonical string/object mode parity and malformed no-publication")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
