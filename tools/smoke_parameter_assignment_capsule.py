#!/usr/bin/env python3
"""Smoke assignment parameters overlay project snapshot parameters in capsules."""

from __future__ import annotations

import tempfile
from pathlib import Path

from specialization_smoke_helpers import read_yaml, require_ok, run_pf, write_project, write_workspace, write_yaml


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="pf-parameter-capsule-") as tmp:
        root = Path(tmp)
        workplace = write_workspace(root)
        project = write_project(root, workplace)
        write_yaml(
            project / ".pf" / "parameters.yaml",
            {
                "schema_version": 1,
                "kind": "processforge.parameters",
                "scope": "project",
                "parameters": {"demo": {"active_profile": "project", "profiles": [{"id": "project", "value": "A"}]}},
            },
        )
        assignment = project / ".pf" / "assignments" / "parameter-task.yaml"
        write_yaml(
            assignment,
            {
                "schema_version": 1,
                "id": "parameter-task",
                "status": "ready",
                "role": "worker",
                "process": "fixture-process",
                "stage": "execute",
                "allowed_files": ["README.md"],
                "forbidden_files": [],
                "required_outputs": [],
                "required_capabilities": [],
                "optional_capabilities": [],
                "parameters": {"demo": {"active_profile": "task", "profiles": [{"id": "project", "value": "B"}]}},
            },
        )
        require_ok(run_pf("project-context-refresh", "--project-root", str(project), "--workplace", str(workplace)))
        require_ok(run_pf("assignment-capsule", "--project-root", str(project), "--assignment", str(assignment)))
        capsule = read_yaml(project / ".pf" / "contexts" / "assignment-capsules" / "parameter-task.capsule.yaml")
        params = capsule["resolved_parameters"]["demo"]
        if params["active_profile"] != "task":
            raise AssertionError("assignment scalar did not override project parameter")
        profile = next(item for item in params["profiles"] if item["id"] == "project")
        if profile["value"] != "B":
            raise AssertionError("assignment list item did not merge by id")
        if "assignment" not in [item["id"] for item in capsule["parameter_resolution_summary"]["sources"]]:
            raise AssertionError("assignment parameter source missing")
    print("PASS: smoke_parameter_assignment_capsule")


if __name__ == "__main__":
    main()
