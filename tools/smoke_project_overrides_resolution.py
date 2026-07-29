#!/usr/bin/env python3
"""Smoke project overrides affect only resolved context."""

from __future__ import annotations

import tempfile
from pathlib import Path

from specialization_smoke_helpers import resolve_json, write_project, write_specialization, write_workspace, write_yaml


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="pf-overrides-resolution-") as tmp:
        root = Path(tmp)
        workplace = write_workspace(root)
        write_specialization(workplace, "fixture.specialization.audit", tool="fixture.tool.b")
        project = write_project(root, workplace)
        write_yaml(project / ".pf" / "project-overrides.yaml", {"schema_version": 1, "kind": "processforge.project_overrides", "overrides": {"tools": [{"target": "fixture.tool.b", "mode": "disable", "reason": "Fixture project disables tool b."}]}})
        resolved = resolve_json(project, workplace, "fixture.specialization.audit")
        if "fixture.tool.b" in resolved["activated_tools"]:
            raise AssertionError("disabled tool remained activated")
        if "fixture.tool.b" not in resolved["excluded_tools"]:
            raise AssertionError("disabled tool missing from excluded_tools")
    print("PASS: smoke_project_overrides_resolution")


if __name__ == "__main__":
    main()
