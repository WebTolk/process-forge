#!/usr/bin/env python3
"""Verify immutable 1.1.0 asset URLs and archive integrity metadata."""

from __future__ import annotations

import argparse
from pathlib import Path

from release_metadata_contract import (
    ARCHIVE_NAME,
    ASSET_BASE_URL,
    RELEASE_VERSION,
    SIDECAR_NAME,
    load_json,
    release_version,
    sha256_file,
)


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=str(root))
    parser.add_argument("--manifest")
    parser.add_argument("--archive")
    args = parser.parse_args()
    root = Path(args.root).resolve()
    manifest_path = Path(args.manifest).resolve() if args.manifest else root / "release" / "updates" / "processforge-stable.json"
    archive = Path(args.archive).resolve() if args.archive else root / "dist" / ARCHIVE_NAME
    manifest = load_json(manifest_path)
    version = release_version(manifest)
    if version.get("channels") != ["stable"] or version.get("prerelease") is not False or version.get("yanked") is not False:
        raise AssertionError("1.1.0 is not the sole active stable release")
    artifacts = version.get("artifacts")
    if not isinstance(artifacts, list) or len(artifacts) != 1 or not isinstance(artifacts[0], dict):
        raise AssertionError("stable release must contain exactly one ZIP artifact")
    artifact = artifacts[0]
    expected_url = f"{ASSET_BASE_URL}/{ARCHIVE_NAME}"
    expected_provenance = f"{ASSET_BASE_URL}/{SIDECAR_NAME}"
    if artifact.get("url") != expected_url or artifact.get("provenance_url") != expected_provenance:
        raise AssertionError("stable manifest URLs are not immutable v1.1.0 GitHub Release assets")
    if artifact.get("sha256") != sha256_file(archive) or artifact.get("size") != archive.stat().st_size:
        raise AssertionError("stable manifest archive hash or size does not match dist artifact")
    if "1.2.0" in manifest_path.read_text(encoding="utf-8") or "1.2.1" in manifest_path.read_text(encoding="utf-8"):
        raise AssertionError("updater-test versions leaked into the stable manifest")
    print(f"PASS: stable manifest points to immutable ProcessForge {RELEASE_VERSION} assets")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
