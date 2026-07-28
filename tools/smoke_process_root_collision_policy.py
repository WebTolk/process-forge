#!/usr/bin/env python3
"""Smoke test duplicate process ids across roots are deterministic and reported."""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from processforge import process_catalog_entries  # noqa: E402


PROCESS = """schema_version: 1
id: duplicate-flow
name: {name}
version: 1.0.0
status: active
description: Duplicate smoke process.
stages: []
roles: []
artifact_definitions: []
gates: []
evolution_policy: stable
"""


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="pf-process-collision-") as raw:
        project = Path(raw)
        (project / ".pf").mkdir()
        (project / ".pf" / "process-forge.yaml").write_text("schema_version: 1\nid: smoke\n", encoding="utf-8")
        for root, name in [("core", "Core Duplicate"), ("user", "User Duplicate")]:
            path = project / "processes" / root / "duplicate-flow.yaml"
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(PROCESS.format(name=name), encoding="utf-8")
        entry = next(item for item in process_catalog_entries(project, strict=True) if item.process_id == "duplicate-flow")
        assert entry.origin == "user"
        assert any("duplicate process_id duplicate-flow" in warning for warning in entry.warnings)
    print("PASS: process root collision policy")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
