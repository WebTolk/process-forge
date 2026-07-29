#!/usr/bin/env python3
"""Smoke specialization definition changes affect project context freshness."""

from __future__ import annotations

import tempfile
from pathlib import Path

from specialization_smoke_helpers import read_yaml, require_ok, run_pf, write_project, write_specialization, write_workspace, write_yaml


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="pf-spec-freshness-") as tmp:
        root = Path(tmp)
        workplace = write_workspace(root)
        write_specialization(workplace, "fixture.specialization.a", tool="fixture.tool.a", provides_capabilities=["fixture.capability.a"])
        project = write_project(root, workplace, specializations=["fixture.specialization.a"])
        require_ok(run_pf("project-context-refresh", "--project-root", str(project), "--workplace", str(workplace)))
        snapshot = read_yaml(project / ".pf" / "contexts" / "project-context.snapshot.yaml")
        selected = snapshot.get("selected_specializations", [])
        if not selected or selected[0].get("sha256") in {"", "missing", None}:
            raise AssertionError("snapshot did not record specialization hash")
        snapshot_id = snapshot.get("snapshot", {}).get("id")

        spec_path = workplace / "specializations" / "fixture.specialization.a.yaml"
        spec = read_yaml(spec_path)
        spec["provides_capabilities"] = ["fixture.capability.a", "fixture.capability.b"]
        write_yaml(spec_path, spec)

        check = require_ok(run_pf("project-context-check", "--project-root", str(project), "--workplace", str(workplace), "--json"))
        if '"status": "stale"' not in check:
            raise AssertionError(check)
        after = read_yaml(project / ".pf" / "contexts" / "project-context.snapshot.yaml")
        if after.get("snapshot", {}).get("id") != snapshot_id:
            raise AssertionError("existing snapshot was not pinned")
    print("PASS: smoke_specialization_freshness_tracks_definition_change")


if __name__ == "__main__":
    main()
