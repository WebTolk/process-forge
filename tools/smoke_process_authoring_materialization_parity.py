#!/usr/bin/env python3
"""Smoke test that process-authoring materializes behavioral fields."""

from __future__ import annotations

import shutil
import sys
import tempfile
from pathlib import Path
from typing import Any

import yaml

from processforge_subprocess import CommandResult, diagnostic_text, run_command as run_processforge_command


ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "tools" / "processforge.py"
ANSWERS = ROOT / "examples" / "process-authoring" / "organized-required-director" / "answers.yaml"


def pf(*args: str, expect: int = 0, timeout: int = 120) -> CommandResult:
    result = run_processforge_command([sys.executable, str(CLI), *args], cwd=ROOT, timeout=timeout)
    if result.timed_out:
        raise AssertionError("timeout: " + " ".join(args) + "\n" + diagnostic_text(result))
    if result.returncode != expect:
        raise AssertionError(f"expected {expect}, got {result.returncode}: {' '.join(args)}\n{diagnostic_text(result)}")
    return result


def load_yaml(path: Path) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return data if isinstance(data, dict) else {}


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="pf-authoring-parity-") as temp:
        root = Path(temp)
        project = root / "project"
        workplace = root / "workplace"
        project.mkdir(parents=True)
        (project / "README.md").write_text("# Authoring parity smoke\n", encoding="utf-8")
        pf("workplace-init", "--workplace", str(workplace), "--apply")
        pf("project-onboard", "--project-root", str(project), "--workplace", str(workplace), "--type", "generic-software-project", "--apply")
        answers = project / "answers.yaml"
        shutil.copyfile(ANSWERS, answers)
        pf("process-create", "--project-root", str(project), "--answers", str(answers), "--apply")
        process_id = load_yaml(answers)["process"]["id"]
        process = load_yaml(project / "processes" / "user" / f"{process_id}.yaml")
        for key in [
            "execution_mode",
            "coordination_requirements",
            "error_handling",
            "responsibility_boundaries",
            "process_transitions",
            "agent_requirements",
            "subagent_policy",
        ]:
            if key not in process:
                raise AssertionError(f"process-authoring dropped behavioral field: {key}")
        report = (project / ".pf" / "authoring" / "processes" / process_id / "apply-report.md").read_text(encoding="utf-8")
        if "processes/user/" not in report or "prompts/" not in report or "docs/processes/" not in report:
            raise AssertionError("apply report does not list materialized process pack files")
        pf("process-doctor", "--project-root", str(project), "--process", process_id, "--contract-only", "--force")
    print("PASS: process-authoring materialization parity smoke")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
