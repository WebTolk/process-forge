#!/usr/bin/env python3
"""Validate the production stable update manifest with the shipped CLI/schema."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=str(root))
    parser.add_argument("--manifest")
    args = parser.parse_args()
    root = Path(args.root).resolve()
    manifest = Path(args.manifest).resolve() if args.manifest else root / "release" / "updates" / "processforge-stable.json"
    result = subprocess.run(
        [sys.executable, str(root / "tools" / "processforge.py"), "update", "manifest", "validate", "--file", str(manifest)],
        cwd=root,
        text=True,
        encoding="utf-8",
        errors="strict",
        capture_output=True,
        timeout=120,
    )
    if result.returncode != 0:
        raise AssertionError(result.stdout + result.stderr)
    print("PASS: stable update manifest satisfies the normalized schema")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
