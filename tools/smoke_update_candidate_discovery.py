#!/usr/bin/env python3
"""Smoke-test local-file update candidate discovery."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

from update_smoke_helpers import make_update_fixture, require_ok, run_pf


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="pf-update-candidates-") as raw:
        workplace = Path(raw)
        make_update_fixture(workplace)
        require_ok(run_pf("update", "candidates", "refresh", "--workplace", str(workplace)))
        data = json.loads((workplace / "runtime" / "update" / "candidates.json").read_text(encoding="utf-8"))
        candidate = data["candidates"][0]
        assert candidate["subject"]["id"] == "acme.software-processes"
        assert candidate["subject"]["type"] == "process_package"
        assert candidate["installed_version"] == "1.0.0"
        assert candidate["available_version"] == "1.1.0"
        assert candidate["manifest_url"].startswith("file:///")
        assert candidate["changelog_url"].startswith("file:///")
        assert candidate["download_url"].startswith("file:///")
        assert len(candidate["sha256"]) == 64
        assert candidate["status"] == "available"
        require_ok(run_pf("update", "candidates", "list", "--workplace", str(workplace)))
        changelog = require_ok(run_pf("update", "changelog", "show", "--workplace", str(workplace), "--candidate", candidate["id"]))
        assert "CHANGELOG_URL: file:///" in changelog
        assert "1.1.0 local deterministic update" in changelog
    print("PASS: update candidate discovery smoke")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
