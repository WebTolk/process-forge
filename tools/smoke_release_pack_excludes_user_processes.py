#!/usr/bin/env python3
"""Smoke test release policy excludes private user/custom process definitions."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from processforge import release_path_is_forbidden  # noqa: E402


def main() -> int:
    assert release_path_is_forbidden("processes/user/private-flow.yaml") == "private user/custom process definition"
    assert release_path_is_forbidden("processes/custom/imported-flow.yaml") == "private user/custom process definition"
    assert release_path_is_forbidden("processes/user/.gitkeep") is None
    assert release_path_is_forbidden("processes/core/task-batch-execution.yaml") is None
    print("PASS: release pack excludes user/custom process definitions")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
