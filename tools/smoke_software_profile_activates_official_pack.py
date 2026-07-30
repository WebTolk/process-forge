#!/usr/bin/env python3
"""Assert the software-development profile activates its official pack."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "bin" / "pf.py"
PACK_ID = "processforge.official.software-development"


def run_pf(*args: str) -> str:
    result = subprocess.run(
        [sys.executable, str(CLI), *args],
        cwd=ROOT,
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        timeout=120,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    return result.stdout + result.stderr


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="pf-software-profile-") as tmp:
        root = Path(tmp)
        workplace = root / "workplace"
        project = root / "project"
        project.mkdir()
        run_pf(
            "workplace-init",
            "--profile",
            "software-development",
            "--workplace",
            str(workplace),
            "--apply",
        )
        active = run_pf(
            "process-list",
            "--origin",
            "official",
            "--active",
            "--workplace",
            str(workplace),
        )
        assert PACK_ID in active, active
        assert "software-feature-development" in active, active
        assert "bug-fix" in active, active
        run_pf("project-init", "--project-root", str(project), "--workplace", str(workplace), "--apply")
        resolved = json.loads(
            run_pf(
                "context-resolve",
                "--project-root",
                str(project),
                "--workplace",
                str(workplace),
                "--process",
                "software-feature-development",
                "--json",
            )
        )
        assert set(resolved["resolved_context"]["activated_knowledge_packages"]) == {
            "docs.php",
            "docs.web.html",
            "docs.web.css",
            "docs.web.javascript",
            "docs.web.accessibility",
            "docs.web.performance",
        }, resolved
    print("PASS: smoke_software_profile_activates_official_pack")


if __name__ == "__main__":
    main()
