#!/usr/bin/env python3
"""Smoke test assignment-derived Codex sandbox and prepared worker prompts."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from unittest.mock import patch

import processforge as pf
from processforge_core.work.worker_assignment import WorkerAssignmentService

_worker_assignment_service = WorkerAssignmentService()
from processforge_core.runtime.drivers import RuntimeDriverDefinitionPolicy
from codex_exec_worker import codex_config_args, managed_hook_trust_args, prompt_payload


def task(*, writer: bool, code: bool, artifacts: bool) -> dict[str, object]:
    return {
        "id": "governed-worker",
        "run_id": "governed-run",
        "process": "task-batch-execution",
        "status": "in_progress",
        "objective": "Use governed knowledge.",
        "ownership": {"writer": writer},
        "execution_mode": {
            "kind": "implementation" if code else "assurance",
            "code_changes_allowed": code,
            "artifact_changes_allowed": artifacts,
        },
        "workspace_access": {"knowledge_resources": ["docs.example:root"]},
        "required_outputs": [
            {
                "id": "report",
                "path": ".pf/artifacts/governed-worker.md",
                "required": True,
            }
        ],
        "expected_report": {"artifact": ".pf/artifacts/governed-worker.md"},
        "agent_model": "gpt-test",
    }


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="pf-codex-governance-") as raw:
        project = Path(raw)
        (project / ".pf" / "assignments").mkdir(parents=True)
        (project / ".pf" / "runs" / "governed-run" / "worker-prompts").mkdir(parents=True)
        writable = task(writer=True, code=True, artifacts=True)
        import processforge_core.common.yaml_io as _core_common_yaml_io

        _core_common_yaml_io.write_yaml_file(project / ".pf" / "assignments" / "governed-worker.yaml", writable)

        driver = RuntimeDriverDefinitionPolicy().default_documents()["codex-exec"]
        from processforge_core.runtime.command import WorkerCommandBuilder
        command, _paths = WorkerCommandBuilder(pf.ROOT).build(project, writable, driver)
        environment = command["command"]["environment"]
        if environment.get("PF_CODEX_SANDBOX") != "workspace-write":
            raise AssertionError(environment)
        if environment.get("PF_CODEX_MEMORIES") != "false":
            raise AssertionError(environment)
        adapter_args = codex_config_args(effort="low", memories="false")
        if 'mcp_servers.processforge.default_tools_approval_mode="approve"' not in adapter_args:
            raise AssertionError(adapter_args)
        if "features.memories=false" not in adapter_args:
            raise AssertionError(adapter_args)

        adapter = (pf.ROOT / "tools" / "pf_runtime" / "codex_hooks.py").resolve()
        command_text = f'py -3 "{adapter}"'
        events = ["SessionStart", "SessionEnd", "PostToolUse", "UserPromptSubmit", "PreCompact", "PostCompact", "Stop", "SubagentStop"]
        hooks = {
            "hooks": {
                event: [{"hooks": [{"type": "command", "command": command_text, "commandWindows": command_text}]}]
                for event in events
            }
        }
        (project / ".codex").mkdir()
        (project / ".codex" / "hooks.json").write_text(json.dumps(hooks), encoding="utf-8")
        if managed_hook_trust_args(project) != ["--dangerously-bypass-hook-trust"]:
            raise AssertionError("PF-managed hooks were not trusted")
        hooks["hooks"]["Stop"][0]["hooks"].append(
            {"type": "command", "command": "foreign-command", "commandWindows": "foreign-command"}
        )
        (project / ".codex" / "hooks.json").write_text(json.dumps(hooks), encoding="utf-8")
        if managed_hook_trust_args(project):
            raise AssertionError("foreign hook must disable automatic trust")

        readonly = task(writer=False, code=False, artifacts=False)
        from processforge_core.runtime.command import WorkerCommandBuilder
        readonly_command, _paths = WorkerCommandBuilder(pf.ROOT).build(project, readonly, driver)
        if readonly_command["command"]["environment"].get("PF_CODEX_SANDBOX") != "read-only":
            raise AssertionError(readonly_command)

        for selected in (writable, readonly):
            for prepared in (None, {"path": ".pf/prepared/fixture.json", "checksum": "sha256:fixture"}):
                with patch.object(WorkerAssignmentService, "load", return_value=selected):
                    prompt = _worker_assignment_service.render_prompt(project, "governed-worker", prepared_input=prepared)
                required = ["PF_PREPARED_INPUT_FILE", "PF_PREPARED_INPUT_SHA256", "Do not bootstrap ProcessForge",
                            "No ProcessForge MCP connection is required", "supplied output delivery contract",
                            "return only its complete content", "For a read-only assignment, do not write the report file yourself",
                            "External resource bodies require explicit grants in the prepared input",
                            "metadata and pointers do not grant permission", "Do not read an extra mutable workspace_access_file",
                            "- workspace_access_file:", "## workspace_access", "## expected_report"]
                missing = [item for item in required if item not in prompt]
                if missing:
                    raise AssertionError({"missing": missing, "prompt": prompt})
                for forbidden in ("`pf.work.start`", "`pf.context`", "Use workspace_access_file for", "Write expected_report."):
                    assert forbidden not in prompt, forbidden
                assert ("not launch-ready" in prompt) == (prepared is None)

        # Prepared Codex uses the fixed wrapper without reading mutable prompt,
        # capsule or workspace-access files, and captures only the final answer.
        prepared = {"kind": "pf.prepared-input", "input": {"marker": "immutable"}}
        with patch("codex_exec_worker.read_text", side_effect=AssertionError("mutable body read")):
            fixed_prompt = prompt_payload(project / "prompt.md", project / "capsule.yaml", project / "access.json", prepared)
        assert "Your final response is captured verbatim" in fixed_prompt
        assert "For a read-only assignment, do not attempt to write the report file yourself" in fixed_prompt
        assert "## Workspace Access File" not in fixed_prompt
        assert json.loads(fixed_prompt.split("## Prepared Execution Input\n\n", 1)[1]) == prepared

        template = pf.load_yaml_document(pf.ROOT / "templates" / "runtime-drivers" / "codex-exec.yaml")
        if template.get("environment", {}).get("variables", {}).get("PF_CODEX_SANDBOX") != "{agent_sandbox}":
            raise AssertionError(template)
        json.dumps(command)
    print("PASS: Codex worker sandbox and prepared input governance")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
