#!/usr/bin/env python3
"""Smoke test process id remains stable after moving from flat to core layout."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from processforge import resolve_process_definition  # noqa: E402


def main() -> int:
    resolved = resolve_process_definition(ROOT, "software-feature-development")
    assert resolved.process_id == "software-feature-development"
    assert resolved.process.get("id") == "software-feature-development"
    assert resolved.path.as_posix().endswith("processes/core/software-feature-development.yaml")
    print("PASS: process id stable after move")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
