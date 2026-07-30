#!/usr/bin/env python3
"""Smoke release-manifest v1 provenance using a temp archive built from clean Git source."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PF = ROOT / "bin" / "pf.py"


def run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(PF), *args],
        cwd=ROOT,
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        check=False,
    )


def git(*args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=ROOT,
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    return result.stdout.strip()


def main() -> int:
    if not (ROOT / ".git").exists():
        print("SKIP: release manifest provenance smoke requires Git source checkout.")
        return 0
    with tempfile.TemporaryDirectory(prefix="pf-release-manifest-v1-") as raw:
        archive = Path(raw) / "processforge.zip"
        packed = run("release-pack", "--root", str(ROOT), "--output", str(archive))
        assert packed.returncode == 0, packed.stdout + packed.stderr
        manifest_path = archive.with_suffix(".manifest.json")
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
        assert data["schema_version"] == 1
        assert data["name"] == "processforge"
        assert data["version"] == (ROOT / "VERSION").read_text(encoding="utf-8").strip()
        assert data["schema_bundle_version"] == "1.0"
        assert data["release_eligible"] is True
        assert data["build"]["deterministic"] is True
        assert data["source"]["vcs"] == "git"
        assert data["source"]["dirty"] is False
        assert data["source"]["commit"] == git("rev-parse", "HEAD")
        assert data["source"]["tree"] == git("rev-parse", "HEAD^{tree}")
        assert data["archive"]["filename"] == archive.name
        assert data["archive"]["format"] == "zip"
        assert data["archive"]["size"] == archive.stat().st_size
        assert data["archive"]["sha256"] == hashlib.sha256(archive.read_bytes()).hexdigest()
        assert data["archive"]["entry_count"] == len(data["files"])
        paths = [item["path"] for item in data["files"]]
        assert paths == sorted(paths)
        assert len(paths) == len(set(paths))
        inspected = run("release-archive-test", "--archive", str(archive), "--root", str(ROOT), "--extracted-test", "skip")
        assert inspected.returncode == 0, inspected.stdout + inspected.stderr
    print("PASS: release manifest v1 provenance contract smoke completed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
