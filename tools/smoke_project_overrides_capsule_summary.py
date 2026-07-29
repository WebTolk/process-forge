#!/usr/bin/env python3
"""Smoke capsule includes project override summary only."""

from __future__ import annotations

import tempfile
from pathlib import Path

from specialization_smoke_helpers import read_yaml, require_ok, run_pf, write_project, write_specialization, write_workspace, write_yaml


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="pf-overrides-capsule-") as tmp:
        root = Path(tmp)
        workplace = write_workspace(root)
        write_specialization(workplace, "fixture.specialization.content", package="fixture.docs.child-content")
        project = write_project(root, workplace, specializations=["fixture.specialization.content"])
        write_yaml(project / ".pf" / "project-overrides.yaml", {"schema_version": 1, "kind": "processforge.project_overrides", "overrides": {"tools": [{"target": "fixture.tool.b", "mode": "disable", "reason": "Fixture project disables tool b."}]}})
        assignment = project / ".pf" / "assignments" / "fixture-task.md"
        assignment.parent.mkdir(parents=True, exist_ok=True)
        assignment.write_text(
            """---
id: fixture-task
status: ready
objective: Fixture
allowed_files:
  - README.md
required_capabilities: []
---
# Fixture
""",
            encoding="utf-8",
        )
        require_ok(run_pf("project-context-refresh", "--project-root", str(project), "--workplace", str(workplace)))
        require_ok(run_pf("assignment-capsule", "--project-root", str(project), "--assignment", str(assignment)))
        capsule = read_yaml(project / ".pf" / "contexts" / "assignment-capsules" / "fixture-task.capsule.yaml")
        if not capsule.get("project_override_summary"):
            raise AssertionError("project override summary missing")
        serialized = str(capsule)
        if "raw override file content" in serialized:
            raise AssertionError("capsule included raw override content")
    print("PASS: smoke_project_overrides_capsule_summary")


if __name__ == "__main__":
    main()
