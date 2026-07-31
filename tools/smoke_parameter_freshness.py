#!/usr/bin/env python3
"""Smoke parameter source changes mark project snapshots stale."""

from __future__ import annotations

import tempfile
from pathlib import Path

from specialization_smoke_helpers import require_ok, run_pf, write_project, write_workspace, write_yaml


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="pf-parameter-freshness-") as tmp:
        root = Path(tmp)
        workplace = write_workspace(root)
        workplace_manifest = workplace / "workplace.yaml"
        write_yaml(
            workplace / "registries" / "parameters.yaml",
            {
                "schema_version": 1,
                "kind": "processforge.parameters",
                "scope": "workplace",
                "parameters": {"demo": {"value": "A"}},
            },
        )
        project = write_project(root, workplace)
        require_ok(run_pf("project-context-refresh", "--project-root", str(project), "--workplace", str(workplace)))
        write_yaml(
            workplace / "registries" / "parameters.yaml",
            {
                "schema_version": 1,
                "kind": "processforge.parameters",
                "scope": "workplace",
                "parameters": {"demo": {"value": "B"}},
            },
        )
        check = require_ok(run_pf("project-context-check", "--project-root", str(project), "--workplace", str(workplace), "--json"))
        if '"status": "stale"' not in check:
            raise AssertionError(check)
        if "workplace-parameter-registry" not in check:
            raise AssertionError("stale reason did not include workplace parameters")
        if not workplace_manifest.is_file():
            raise AssertionError("fixture workplace manifest missing")
    print("PASS: smoke_parameter_freshness")


if __name__ == "__main__":
    main()
