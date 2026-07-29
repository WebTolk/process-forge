#!/usr/bin/env python3
"""Smoke test for the root-aware process directory layout."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from processforge import process_catalog_entries  # noqa: E402


def main() -> int:
    core = ROOT / "processes" / "core"
    user = ROOT / "processes" / "user"
    custom = ROOT / "processes" / "custom"
    assert core.is_dir(), "processes/core missing"
    assert user.is_dir(), "processes/user missing"
    assert custom.is_dir(), "processes/custom missing"
    flat = sorted((ROOT / "processes").glob("*.yaml"))
    assert not flat, f"flat process files remain: {[path.name for path in flat]}"
    entries = process_catalog_entries(ROOT)
    core_ids = {entry.process_id for entry in entries if entry.origin == "core"}
    assert "task-batch-execution" in core_ids, "neutral core process not resolved"
    assert all(entry.path.is_file() for entry in entries), "resolved process path missing"
    print("PASS: process directory layout")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
