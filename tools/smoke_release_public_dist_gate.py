#!/usr/bin/env python3
"""Regression smoke for the public release distribution-artifact gate."""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "tools") not in sys.path:
    sys.path.insert(0, str(ROOT / "tools"))

import processforge


def failures(root: Path) -> list[str]:
    return [item.message for item in processforge.public_release_checks(root) if item.level == "FAIL"]


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="pf-public-dist-") as raw:
        root = Path(raw)
        (root / "VERSION").write_text("1.1.0\n", encoding="utf-8")
        dist = root / "dist"
        dist.mkdir()
        for name in ("processforge-1.1.0.zip", "processforge-1.1.0.manifest.json"):
            (dist / name).write_text("current", encoding="utf-8")
        assert not failures(root), failures(root)
        (dist / "processforge-1.0.9.zip").write_text("stale", encoding="utf-8")
        assert any("processforge-1.0.9.zip" in message for message in failures(root)), failures(root)
    print("PASS: public release gate accepts only current generated dist artifacts")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
