#!/usr/bin/env python3
"""Smoke test for ProcessForge runtime driver registry MVP."""

from __future__ import annotations

import sys
from pathlib import Path

from processforge_subprocess import CommandResult, diagnostic_text, run_command as run_processforge_command


ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "tools" / "processforge.py"


def pf(*args: str, expect: int = 0) -> CommandResult:
    result = run_processforge_command([sys.executable, str(CLI), *args], cwd=ROOT, timeout=60)
    if result.returncode != expect:
        raise AssertionError(f"expected {expect}, got {result.returncode}: {' '.join(args)}\n{diagnostic_text(result)}")
    return result


def main() -> int:
    listed = pf("runtime-driver", "list", "--project-root", str(ROOT)).stdout
    for driver_id in ["manual", "generic-shell", "test-echo-worker"]:
        if driver_id not in listed:
            raise AssertionError(f"missing runtime driver in list: {driver_id}")
        pf("runtime-driver", "validate", "--project-root", str(ROOT), "--driver", driver_id)
        described = pf("runtime-driver", "describe", "--project-root", str(ROOT), "--driver", driver_id).stdout
        if f"id: {driver_id}" not in described:
            raise AssertionError(f"describe output missing id: {driver_id}")
    print("PASS: runtime driver registry smoke")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
