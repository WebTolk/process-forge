#!/usr/bin/env python3
"""Shared contract helpers for ProcessForge release metadata smokes."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


PRODUCT_ID = "processforge"
RELEASE_VERSION = "1.1.0"
RELEASE_TAG = "v1.1.0"
REPOSITORY = "WebTolk/process-forge"
ASSET_BASE_URL = f"https://github.com/{REPOSITORY}/releases/download/{RELEASE_TAG}"
ARCHIVE_NAME = f"processforge-{RELEASE_VERSION}.zip"
SIDECAR_NAME = f"processforge-{RELEASE_VERSION}.manifest.json"


def load_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise AssertionError(f"expected JSON object: {path}")
    return data


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def release_version(manifest: dict[str, Any]) -> dict[str, Any]:
    subjects = manifest.get("subjects")
    if not isinstance(subjects, list) or len(subjects) != 1:
        raise AssertionError("stable manifest must contain exactly one subject")
    subject = subjects[0]
    if not isinstance(subject, dict) or subject.get("id") != PRODUCT_ID:
        raise AssertionError("stable manifest subject is not ProcessForge")
    versions = subject.get("versions")
    if not isinstance(versions, list) or len(versions) != 1:
        raise AssertionError("stable manifest must expose exactly one version")
    version = versions[0]
    if not isinstance(version, dict) or version.get("version") != RELEASE_VERSION:
        raise AssertionError("stable manifest does not expose only 1.1.0")
    return version
