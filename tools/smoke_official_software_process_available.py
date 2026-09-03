#!/usr/bin/env python3
"""Exercise distribution discovery for the official software process."""

from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "bin" / "pf.py"
PROCESS_ID = "software-feature-development"
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
    listed = run_pf("process-list", "--origin", "official", "--available")
    assert PROCESS_ID in listed, listed
    assert PACK_ID in listed, listed
    assert "official" in listed.lower(), listed

    shown = run_pf("process-show", PROCESS_ID)
    assert PROCESS_ID in shown, shown
    assert PACK_ID in shown, shown
    assert "origin" in shown.lower() and "official" in shown.lower(), shown
    kernel = run_pf("process-list", "--origin", "kernel")
    assert "\tkernel\t" in kernel, kernel
    assert "\tcore\t" not in kernel, kernel

    with tempfile.TemporaryDirectory(prefix="pf-official-show-workplace-") as tmp:
        neutral_workplace = Path(tmp) / "neutral-workplace"
        run_pf("workplace-init", "--workplace", str(neutral_workplace), "--apply")
        direct = run_pf(
            "process-show",
            "packs/official/software-development/processes/software-feature-development.yaml",
            "--workplace",
            str(neutral_workplace),
        )
        assert "ORIGIN: official" in direct, direct
        assert f"PACK_ID: {PACK_ID}" in direct, direct
        assert "ACTIVE: false" in direct, direct
        assert "PRODUCTION_READY: true" in direct, direct

        workplace = Path(tmp) / "software-workplace"
        run_pf(
            "workplace-init",
            "--profile",
            "software-development",
            "--workplace",
            str(workplace),
            "--apply",
        )
        active = run_pf("process-show", PROCESS_ID, "--workplace", str(workplace))
        assert "ACTIVE: true" in active, active
    print("PASS: smoke_official_software_process_available")


if __name__ == "__main__":
    main()
