#!/usr/bin/env python3
"""Smoke assignment capsule receives specialization and override summaries."""

from __future__ import annotations

import tempfile
from pathlib import Path

from specialization_smoke_helpers import read_yaml, require_ok, run_pf, write_project, write_specialization, write_workspace


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="pf-spec-capsule-") as tmp:
        root = Path(tmp)
        workplace = write_workspace(root)
        write_specialization(workplace, "fixture.specialization.dev", tool="fixture.tool.a")
        project = write_project(root, workplace, specializations=["fixture.specialization.dev"])
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
        if not capsule.get("effective_specializations"):
            raise AssertionError("capsule missing effective_specializations")
        for key in ["active_resource_profile", "execution_route_summary", "capability_resolution_summary"]:
            if key not in capsule:
                raise AssertionError(f"capsule missing {key}")
        if "fixture.tool.a" not in [item.get("id") for item in capsule.get("effective_resources", [])]:
            raise AssertionError("capsule missing activated resource summary")
    print("PASS: smoke_specialization_capsule_activation")


if __name__ == "__main__":
    main()
