#!/usr/bin/env python3
"""Smoke test assignment-derived Codex sandbox and PF-first worker prompts."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import processforge as pf
from codex_exec_worker import codex_config_args, managed_hook_trust_args


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
        pf.write_yaml_file(project / ".pf" / "assignments" / "governed-worker.yaml", writable)

        driver = pf.default_runtime_driver_documents()["codex-exec"]
        command, _paths = pf.build_worker_process_command(project, writable, driver)
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
        readonly_command, _paths = pf.build_worker_process_command(project, readonly, driver)
        if readonly_command["command"]["environment"].get("PF_CODEX_SANDBOX") != "read-only":
            raise AssertionError(readonly_command)

        prompt = pf.render_worker_launch_prompt(project, "governed-worker")
        required = ["`pf.context`", "`pf.work.start`", "`pf.resolve`", "`pf.search`", "Do not silently fall back"]
        missing = [item for item in required if item not in prompt]
        if missing:
            raise AssertionError({"missing": missing, "prompt": prompt})

        template = pf.load_yaml_document(pf.ROOT / "templates" / "runtime-drivers" / "codex-exec.yaml")
        if template.get("environment", {}).get("variables", {}).get("PF_CODEX_SANDBOX") != "{agent_sandbox}":
            raise AssertionError(template)
        json.dumps(command)
    print("PASS: Codex worker sandbox and PF-first governance")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
