#!/usr/bin/env python3
"""Smoke test process-list origin output and filters."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    command = [sys.executable, str(ROOT / "bin" / "pf.py"), "process-list", "--project-root", str(ROOT), "--origin", "core"]
    result = subprocess.run(command, cwd=ROOT, text=True, capture_output=True, timeout=60)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "origin" in result.stdout.splitlines()[0], result.stdout
    assert "task-batch-execution" in result.stdout, result.stdout
    assert "\tcore\t" in result.stdout, result.stdout
    user = subprocess.run(command[:-1] + ["user", "--all"], cwd=ROOT, text=True, capture_output=True, timeout=60)
    assert user.returncode == 0, user.stdout + user.stderr
    assert "No processes found." in user.stdout or "\tuser\t" in user.stdout
    print("PASS: process-list origin filters")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
