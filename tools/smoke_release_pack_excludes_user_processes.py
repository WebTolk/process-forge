#!/usr/bin/env python3
"""Smoke test release policy excludes private user/custom process definitions."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))


def main() -> int:
    from processforge_core.maintenance.release_sources import ReleaseSourcePolicy

    assert ReleaseSourcePolicy().release_path_is_forbidden("processes/user/private-flow.yaml") == "private user/custom process definition"
    assert ReleaseSourcePolicy().release_path_is_forbidden("processes/custom/imported-flow.yaml") == "private user/custom process definition"
    assert ReleaseSourcePolicy().release_path_is_forbidden("processes/user/.gitkeep") is None
    assert ReleaseSourcePolicy().release_path_is_forbidden("processes/core/task-batch-execution.yaml") is None
    print("PASS: release pack excludes user/custom process definitions")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
