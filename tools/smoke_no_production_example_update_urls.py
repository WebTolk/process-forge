#!/usr/bin/env python3
"""Reject placeholder domains from production ProcessForge update metadata."""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    candidates = [ROOT / "updates" / "processforge-update-index.yaml"]
    release_root = ROOT / "release"
    if release_root.is_dir():
        candidates.extend(path for path in release_root.rglob("*") if path.is_file())
    failures: list[str] = []
    for path in candidates:
        text = path.read_text(encoding="utf-8", errors="replace").lower()
        if "example.com/processforge" in text:
            failures.append(path.relative_to(ROOT).as_posix())
    if failures:
        raise AssertionError(f"placeholder production update URLs: {failures}")
    print("PASS: production ProcessForge update metadata has no placeholder URLs")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
