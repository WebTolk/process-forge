#!/usr/bin/env python3
"""Smoke test process authoring writes generated processes to processes/user."""

from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="pf-authoring-user-root-") as raw:
        project = Path(raw)
        (project / ".pf").mkdir()
        (project / ".pf" / "process-forge.yaml").write_text("schema_version: 1\nid: smoke\n", encoding="utf-8")
        command = [
            sys.executable,
            str(ROOT / "bin" / "pf.py"),
            "process-create",
            "--project-root",
            str(project),
            "--answers",
            str(ROOT / "templates" / "process-authoring-answers.yaml"),
            "--apply",
        ]
        result = subprocess.run(command, cwd=ROOT, text=True, capture_output=True, timeout=60)
        assert result.returncode == 0, result.stdout + result.stderr
        generated = project / "processes" / "user" / "quality-audit.yaml"
        assert generated.is_file(), result.stdout
        assert not (project / "processes" / "core" / "quality-audit.yaml").exists(), "normal authoring wrote to core"
        definition = yaml.safe_load(generated.read_text(encoding="utf-8"))
        transitions = definition.get("process_transitions")
        assert isinstance(transitions, list), transitions
        assert transitions == [
            {
                "id": "quality-audit-to-review",
                "from_process": "quality-audit",
                "to_process": "task-batch-execution",
                "mode": "wait_for_result",
                "requires_agent": {"required_role": "reviewer"},
                "input_contract": {"artifacts": ["audit-report"]},
                "output_contract": {"artifacts": ["audit-review"]},
                "return": {
                    "offline_agent_policy": "keep_waiting_then_needs_operator",
                    "continuation_capsule_required": True,
                    "post_handoff_run_owner": "source_process",
                },
            }
        ], transitions
    print("PASS: process authoring writes user root")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
