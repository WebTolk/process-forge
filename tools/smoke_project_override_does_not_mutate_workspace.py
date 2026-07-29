#!/usr/bin/env python3
"""Smoke project overrides do not mutate workspace resources or other projects."""

from __future__ import annotations

import tempfile
from pathlib import Path

from specialization_smoke_helpers import read_yaml, resolve_json, write_project, write_specialization, write_workspace, write_yaml


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="pf-overrides-isolation-") as tmp:
        root = Path(tmp)
        workplace = write_workspace(root)
        write_specialization(workplace, "fixture.specialization.audit", tool="fixture.tool.b")
        before = read_yaml(workplace / "specializations" / "fixture.specialization.audit.yaml")
        project_a = write_project(root / "a", workplace)
        project_b = write_project(root / "b", workplace)
        write_yaml(project_a / ".pf" / "project-overrides.yaml", {"schema_version": 1, "kind": "processforge.project_overrides", "overrides": {"tools": [{"target": "fixture.tool.b", "mode": "disable", "reason": "Fixture project disables tool b."}]}})
        resolved_a = resolve_json(project_a, workplace, "fixture.specialization.audit")
        resolved_b = resolve_json(project_b, workplace, "fixture.specialization.audit")
        after = read_yaml(workplace / "specializations" / "fixture.specialization.audit.yaml")
        if before != after:
            raise AssertionError("workspace specialization mutated")
        if "fixture.tool.b" in resolved_a["activated_tools"]:
            raise AssertionError("override did not affect project A")
        if "fixture.tool.b" not in resolved_b["activated_tools"]:
            raise AssertionError("override leaked to project B")
    print("PASS: smoke_project_override_does_not_mutate_workspace")


if __name__ == "__main__":
    main()
