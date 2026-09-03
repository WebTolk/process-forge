#!/usr/bin/env python3
"""Ensure mutable/historical repository metadata is not embedded in the ZIP."""

from __future__ import annotations

import argparse
import zipfile
from pathlib import Path

from release_metadata_contract import SIDECAR_NAME


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--archive", required=True)
    args = parser.parse_args()
    archive = Path(args.archive).resolve()
    with zipfile.ZipFile(archive) as bundle:
        names = set(bundle.namelist())
    forbidden = sorted(name for name in names if name.startswith("release/") or name.endswith("/" + SIDECAR_NAME) or name == SIDECAR_NAME)
    if forbidden:
        raise AssertionError(f"release metadata leaked into archive: {forbidden}")
    print("PASS: repository release metadata is outside the distribution archive")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
