#!/usr/bin/env python3
"""Smoke test for strict process definition contract checks."""

from __future__ import annotations

import copy
import sys
import tempfile
from pathlib import Path
from typing import Any

import yaml

from processforge_subprocess import CommandResult, diagnostic_text, run_command as run_processforge_command


ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "tools" / "processforge.py"


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


def write_yaml(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=False), encoding="utf-8")


def bootstrap(root: Path) -> Path:
    project = root / "project"
    workplace = root / "workplace"
    project.mkdir(parents=True)
    (project / "README.md").write_text("# Schema contract smoke\n", encoding="utf-8")
    pf("workplace-init", "--workplace", str(workplace), "--apply")
    pf("project-onboard", "--project-root", str(project), "--workplace", str(workplace), "--type", "generic-software-project", "--apply")
    return project


def main() -> int:
    source = load_yaml(ROOT / "processes" / "bug-fix.yaml")
    with tempfile.TemporaryDirectory(prefix="pf-process-schema-contract-") as temp:
        project = bootstrap(Path(temp))
        valid = copy.deepcopy(source)
        valid["id"] = "valid-contract-process"
        write_yaml(project / "processes" / "valid-contract-process.yaml", valid)
        (project / "prompts").mkdir(parents=True, exist_ok=True)
        (project / "docs" / "processes").mkdir(parents=True, exist_ok=True)
        (project / "examples" / "process-authoring" / "valid-contract-process").mkdir(parents=True, exist_ok=True)
        (project / "prompts" / "valid-contract-process-agent.md").write_text("# Companion\n", encoding="utf-8")
        (project / "docs" / "processes" / "valid-contract-process.md").write_text("# Companion\n", encoding="utf-8")
        (project / "examples" / "process-authoring" / "valid-contract-process" / "README.md").write_text("# Example\n", encoding="utf-8")
        pf("process-doctor", "--project-root", str(project), "--process", "valid-contract-process", "--contract-only")

        missing_artifact = copy.deepcopy(valid)
        missing_artifact["id"] = "missing-artifact-process"
        missing_artifact["stages"][0]["produced_artifacts"].append("not-declared")
        write_yaml(project / "processes" / "missing-artifact-process.yaml", missing_artifact)
        result = pf("process-doctor", "--project-root", str(project), "--process", "missing-artifact-process", "--contract-only", expect=1)
        if "produced artifacts declared" not in result.stdout:
            raise AssertionError("missing artifact definition did not fail strict contract")

        deprecated = copy.deepcopy(valid)
        deprecated["id"] = "deprecated-handoff-process"
        deprecated["stages"][0]["handoff_required"] = True
        write_yaml(project / "processes" / "deprecated-handoff-process.yaml", deprecated)
        result = pf("process-doctor", "--project-root", str(project), "--process", "deprecated-handoff-process", "--contract-only", expect=1)
        if "deprecated handoff_required" not in result.stdout:
            raise AssertionError("deprecated handoff_required did not fail strict contract")
    print("PASS: process definition schema contract smoke")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
