#!/usr/bin/env python3
"""Prove doctor-project can distinguish registry gaps from explicit runtime-access waivers."""

from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "bin" / "pf.py"


def run_pf(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(CLI), *args],
        cwd=ROOT,
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        timeout=120,
        check=False,
    )


def require_ok(result: subprocess.CompletedProcess[str]) -> str:
    if result.returncode != 0:
        raise AssertionError(result.stdout + result.stderr)
    return result.stdout + result.stderr


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="pf-cap-waiver-") as tmp:
        root = Path(tmp)
        workplace = root / "workplace"
        project = root / "project"
        answers = root / "answers.yaml"
        project.mkdir()
        answers.write_text(
            yaml.safe_dump(
                {
                    "schema_version": 1,
                    "project": {"id": "capability-waiver-fixture", "name": "Capability Waiver Fixture", "type": "generic"},
                    "required_capabilities": ["filesystem.read", "filesystem.write"],
                    "optional_capabilities": [],
                },
                sort_keys=False,
            ),
            encoding="utf-8",
        )

        require_ok(run_pf("workplace-init", "--profile", "generic", "--workplace", str(workplace), "--apply"))
        init = run_pf("project-init", "--project-root", str(project), "--workplace", str(workplace), "--answers", str(answers), "--apply")
        if not (project / ".pf" / "artifacts" / "global-resource-matching-report.md").is_file():
            raise AssertionError(init.stdout + init.stderr)
        if "registry declarations are missing" not in init.stdout:
            raise AssertionError(init.stdout + init.stderr)

        before = run_pf("doctor-project", "--project-root", str(project))
        if before.returncode == 0:
            raise AssertionError(before.stdout + before.stderr)
        if "registry declarations are missing" not in before.stdout:
            raise AssertionError(before.stdout + before.stderr)

        waiver_path = project / ".pf" / "artifacts" / "capability-waivers.yaml"
        waiver_path.write_text(
            yaml.safe_dump(
                {
                    "schema_version": 1,
                    "capability_waivers": [
                        {
                            "capability": "filesystem.read",
                            "status": "active",
                            "reason": "runtime access verified in local automation",
                            "evidence": ".pf/artifacts/delivery-report.md",
                        },
                        {
                            "capability": "filesystem.write",
                            "status": "active",
                            "reason": "runtime access verified in local automation",
                            "evidence": ".pf/artifacts/delivery-report.md",
                        },
                    ],
                },
                sort_keys=False,
            ),
            encoding="utf-8",
        )
        after = run_pf("doctor-project", "--project-root", str(project))
        if after.returncode != 0:
            raise AssertionError(after.stdout + after.stderr)
        if "explicit runtime-access waiver" not in after.stdout:
            raise AssertionError(after.stdout + after.stderr)
    print("PASS: smoke_doctor_project_capability_waiver")


if __name__ == "__main__":
    main()
