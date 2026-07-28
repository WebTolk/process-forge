#!/usr/bin/env python3
"""Smoke test legacy flat process files are loaded with warnings."""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from processforge import process_catalog_entries  # noqa: E402


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="pf-legacy-flat-") as raw:
        project = Path(raw)
        (project / ".pf").mkdir()
        (project / ".pf" / "process-forge.yaml").write_text("schema_version: 1\nid: smoke\n", encoding="utf-8")
        process_root = project / "processes"
        process_root.mkdir()
        (process_root / "legacy-flow.yaml").write_text(
            "schema_version: 1\nid: legacy-flow\nname: Legacy Flow\nversion: 1.0.0\nstatus: active\ndescription: Legacy.\nstages: []\nroles: []\nartifact_definitions: []\ngates: []\nevolution_policy: stable\n",
            encoding="utf-8",
        )
        entry = next(item for item in process_catalog_entries(project) if item.process_id == "legacy-flow")
        assert entry.origin == "legacy_flat"
        assert any("Legacy flat process path detected" in warning for warning in entry.warnings)
    print("PASS: legacy flat process layout warning")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
