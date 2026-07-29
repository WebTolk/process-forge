#!/usr/bin/env python3
"""Smoke test a neutral process id remains stable in the core layout."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from processforge import resolve_process_definition  # noqa: E402


def main() -> int:
    resolved = resolve_process_definition(ROOT, "task-batch-execution")
    assert resolved.process_id == "task-batch-execution"
    assert resolved.process.get("id") == "task-batch-execution"
    assert resolved.path.as_posix().endswith("processes/core/task-batch-execution.yaml")
    print("PASS: process id stable after move")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
