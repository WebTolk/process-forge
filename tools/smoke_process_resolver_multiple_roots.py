#!/usr/bin/env python3
"""Smoke test process resolver precedence across core/user/custom roots."""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from processforge import process_catalog_entries, resolve_process_definition  # noqa: E402


PROCESS = """schema_version: 1
id: {process_id}
name: {name}
version: 1.0.0
status: active
description: Smoke process.
stages: []
roles: []
artifact_definitions: []
gates: []
evolution_policy: stable
"""


def write_process(root: Path, process_id: str, name: str) -> Path:
    path = root / f"{process_id}.yaml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(PROCESS.format(process_id=process_id, name=name), encoding="utf-8")
    return path


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="pf-process-roots-") as raw:
        project = Path(raw)
        (project / ".pf").mkdir()
        (project / ".pf" / "process-forge.yaml").write_text("schema_version: 1\nid: smoke\n", encoding="utf-8")
        write_process(project / "processes" / "core", "shared-flow", "Core Flow")
        write_process(project / "processes" / "user", "user-flow", "User Flow")
        write_process(project / "processes" / "custom", "custom-flow", "Custom Flow")
        entries = process_catalog_entries(project)
        origins = {entry.process_id: entry.origin for entry in entries}
        assert origins["shared-flow"] == "core"
        assert origins["user-flow"] == "user"
        assert origins["custom-flow"] == "custom"
        resolved = resolve_process_definition(project, "user-flow")
        assert resolved.origin == "user"
        assert resolved.root.name == "user"
    print("PASS: process resolver multiple roots")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
