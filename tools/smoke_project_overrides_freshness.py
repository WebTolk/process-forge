#!/usr/bin/env python3
"""Smoke project override changes mark snapshot stale."""

from __future__ import annotations

import tempfile
from pathlib import Path

from specialization_smoke_helpers import read_yaml, require_ok, run_pf, write_project, write_specialization, write_workspace, write_yaml


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="pf-overrides-freshness-") as tmp:
        root = Path(tmp)
        workplace = write_workspace(root)
        write_specialization(workplace, "fixture.specialization.content", package="fixture.docs.child-content")
        project = write_project(root, workplace, specializations=["fixture.specialization.content"])
        override_path = project / ".pf" / "specializations" / "overrides" / "content.yaml"
        write_yaml(override_path, {"schema_version": 1, "note": "A"})
        write_yaml(project / ".pf" / "project-overrides.yaml", {"schema_version": 1, "kind": "processforge.project_overrides", "overrides": {"specializations": [{"target": "fixture.specialization.content", "mode": "overlay", "path": ".pf/specializations/overrides/content.yaml", "reason": "Fixture override."}]}})
        require_ok(run_pf("project-context-refresh", "--project-root", str(project), "--workplace", str(workplace)))
        snapshot_id = read_yaml(project / ".pf" / "contexts" / "project-context.snapshot.yaml").get("snapshot", {}).get("id")
        write_yaml(override_path, {"schema_version": 1, "note": "B"})
        check = require_ok(run_pf("project-context-check", "--project-root", str(project), "--workplace", str(workplace), "--json"))
        if '"status": "stale"' not in check:
            raise AssertionError(check)
        if read_yaml(project / ".pf" / "contexts" / "project-context.snapshot.yaml").get("snapshot", {}).get("id") != snapshot_id:
            raise AssertionError("existing snapshot was not pinned before refresh")
    print("PASS: smoke_project_overrides_freshness")


if __name__ == "__main__":
    main()
