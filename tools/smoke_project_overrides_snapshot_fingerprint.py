#!/usr/bin/env python3
"""Smoke project override fingerprints change with override files."""

from __future__ import annotations

import tempfile
from pathlib import Path

from specialization_smoke_helpers import read_yaml, require_ok, run_pf, write_project, write_specialization, write_workspace, write_yaml


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="pf-overrides-fingerprint-") as tmp:
        root = Path(tmp)
        workplace = write_workspace(root)
        write_specialization(workplace, "fixture.specialization.content", package="fixture.docs.child-content")
        project = write_project(root, workplace, specializations=["fixture.specialization.content"])
        override_path = project / ".pf" / "specializations" / "overrides" / "content.yaml"
        write_yaml(override_path, {"schema_version": 1, "note": "A"})
        write_yaml(project / ".pf" / "project-overrides.yaml", {"schema_version": 1, "kind": "processforge.project_overrides", "overrides": {"specializations": [{"target": "fixture.specialization.content", "mode": "overlay", "path": ".pf/specializations/overrides/content.yaml", "reason": "Fixture override."}]}})
        require_ok(run_pf("project-context-refresh", "--project-root", str(project), "--workplace", str(workplace)))
        first = read_yaml(project / ".pf" / "contexts" / "project-context.snapshot.yaml")
        write_yaml(override_path, {"schema_version": 1, "note": "B"})
        require_ok(run_pf("project-context-refresh", "--project-root", str(project), "--workplace", str(workplace)))
        second = read_yaml(project / ".pf" / "contexts" / "project-context.snapshot.yaml")
        key = "specializations:fixture.specialization.content"
        if first.get("effective_fingerprints", {}).get(key) == second.get("effective_fingerprints", {}).get(key):
            raise AssertionError("effective fingerprint did not change")
        record = second.get("applied_project_overrides", [])[0]
        if record.get("base_sha256") == "missing" or record.get("sha256") == "missing":
            raise AssertionError("base or override hash missing")
    print("PASS: smoke_project_overrides_snapshot_fingerprint")


if __name__ == "__main__":
    main()
