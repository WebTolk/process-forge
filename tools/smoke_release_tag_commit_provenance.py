#!/usr/bin/env python3
"""Match the release sidecar source commit to the final Git tag."""

from __future__ import annotations

import argparse
import subprocess
from pathlib import Path

from release_metadata_contract import RELEASE_TAG, RELEASE_VERSION, SIDECAR_NAME, load_json


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=str(root))
    parser.add_argument("--manifest")
    parser.add_argument("--tag", default=RELEASE_TAG)
    args = parser.parse_args()
    root = Path(args.root).resolve()
    manifest = Path(args.manifest).resolve() if args.manifest else root / "release" / RELEASE_VERSION / SIDECAR_NAME
    sidecar = load_json(manifest)
    tagged = subprocess.run(
        ["git", "rev-list", "-n", "1", args.tag], cwd=root, text=True, encoding="utf-8", errors="strict", capture_output=True, check=True
    ).stdout.strip()
    source = sidecar.get("source") if isinstance(sidecar.get("source"), dict) else {}
    if source.get("commit") != tagged:
        raise AssertionError(f"sidecar source commit {source.get('commit')} != {args.tag} commit {tagged}")
    print(f"PASS: release sidecar provenance matches {args.tag} at {tagged}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
