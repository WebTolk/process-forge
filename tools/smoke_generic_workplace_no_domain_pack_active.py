#!/usr/bin/env python3
"""Assert generic workplace init keeps official domain packs inactive."""

from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "bin" / "pf.py"
DOMAIN_PROCESS_IDS = {
    "software-feature-development",
    "bug-fix",
    "testing",
    "content-production",
    "documentation-mirror-import",
}


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
    with tempfile.TemporaryDirectory(prefix="pf-generic-official-pack-") as tmp:
        workplace = Path(tmp) / "workplace"
        run_pf(
            "workplace-init",
            "--profile",
            "generic",
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
        assert not any(process_id in active for process_id in DOMAIN_PROCESS_IDS), active

        registry_path = workplace / "registries" / "project-classifiers.yaml"
        registry = yaml.safe_load(registry_path.read_text(encoding="utf-8"))
        assert registry.get("project_classifiers") == [], registry
    print("PASS: smoke_generic_workplace_no_domain_pack_active")


if __name__ == "__main__":
    main()
