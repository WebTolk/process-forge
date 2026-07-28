#!/usr/bin/env python3
"""Smoke test for built-in process pack companions and package references."""

from __future__ import annotations

import json
import sys
from pathlib import Path

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


def main() -> int:
    report = json.loads(pf("builtin-process-catalog-doctor", "--root", str(ROOT), "--public", "--json").stdout)
    process_ids = {item["id"] for item in report["processes"]}
    for item in report["processes"]:
        if item["classification"] != "PUBLIC_STABLE":
            continue
        for field in ["has_prompt", "has_process_doc", "has_authoring_example", "artifact_definitions_complete", "stage_artifacts_declared", "gates_valid"]:
            if not item[field]:
                raise AssertionError(f"{item['id']} failed completeness field {field}")
    for package in (ROOT / "packages").glob("*.yaml"):
        text = package.read_text(encoding="utf-8")
        for process_id in process_ids:
            if f"- {process_id}\n" in text and not (ROOT / "processes" / "core" / f"{process_id}.yaml").is_file():
                raise AssertionError(f"{package} references missing process {process_id}")
    print("PASS: built-in process pack completeness smoke")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
