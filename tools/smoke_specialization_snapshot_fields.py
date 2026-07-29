#!/usr/bin/env python3
"""Smoke project snapshot records specialization fields."""

from __future__ import annotations

import tempfile
from pathlib import Path

from specialization_smoke_helpers import read_yaml, require_ok, run_pf, write_project, write_specialization, write_workspace


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="pf-spec-snapshot-") as tmp:
        root = Path(tmp)
        workplace = write_workspace(root)
        write_specialization(workplace, "fixture.specialization.dev", tool="fixture.tool.a")
        project = write_project(root, workplace, specializations=["fixture.specialization.dev"])
        require_ok(run_pf("project-context-refresh", "--project-root", str(project), "--workplace", str(workplace)))
        snapshot = read_yaml(project / ".pf" / "contexts" / "project-context.snapshot.yaml")
        if not snapshot.get("selected_specializations"):
            raise AssertionError("selected_specializations missing")
        for key in ["active_resource_profile", "execution_route", "capability_resolution"]:
            if key not in snapshot:
                raise AssertionError(f"{key} missing")
        if "fixture.tool.a" not in snapshot.get("resolved_context", {}).get("activated_tools", []):
            raise AssertionError("activated tool missing from resolved_context")
    print("PASS: smoke_specialization_snapshot_fields")


if __name__ == "__main__":
    main()
