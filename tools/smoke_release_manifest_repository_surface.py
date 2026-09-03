#!/usr/bin/env python3
"""Verify that repository release metadata and final distribution artifacts exist."""

from __future__ import annotations

import argparse
from pathlib import Path

from release_metadata_contract import ARCHIVE_NAME, RELEASE_VERSION, SIDECAR_NAME, load_json


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=str(Path(__file__).resolve().parents[1]))
    args = parser.parse_args()
    root = Path(args.root).resolve()
    paths = [
        root / "dist" / ARCHIVE_NAME,
        root / "dist" / SIDECAR_NAME,
        root / "release" / RELEASE_VERSION / SIDECAR_NAME,
        root / "release" / "updates" / "processforge-stable.json",
    ]
    missing = [str(path) for path in paths if not path.is_file()]
    if missing:
        raise AssertionError("missing release surface: " + ", ".join(missing))
    sidecar = load_json(paths[1])
    historical = load_json(paths[2])
    if sidecar != historical:
        raise AssertionError("historical release sidecar differs from the shipped sidecar")
    print("PASS: repository release metadata surface is complete")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
