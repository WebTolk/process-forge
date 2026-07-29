#!/usr/bin/env python3
"""Smoke project specialization overlay changes the effective resource profile."""

from __future__ import annotations

import tempfile
from pathlib import Path

from specialization_smoke_helpers import resolve_json, write_process_with_capability, write_project, write_specialization, write_workspace, write_yaml


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="pf-spec-override-applies-") as tmp:
        root = Path(tmp)
        workplace = write_workspace(root)
        write_specialization(workplace, "fixture.specialization.a", tool="fixture.tool.a", provides_capabilities=["fixture.capability.a"])
        project = write_project(root, workplace)
        write_process_with_capability(project, capability="fixture.capability.b")
        overlay_path = project / ".pf" / "specializations" / "overrides" / "a.yaml"
        write_yaml(
            overlay_path,
            {
                "schema_version": 1,
                "resources": {
                    "requires": {"knowledge_packages": [], "tools": [], "mcp": [], "templates": []},
                    "recommends": {"knowledge_packages": [], "tools": ["fixture.tool.b"], "mcp": [], "templates": []},
                    "optional": {"knowledge_packages": [], "tools": [], "mcp": [], "templates": []},
                    "excludes": {"knowledge_packages": [], "tools": ["fixture.tool.a"], "mcp": [], "templates": []},
                },
                "provides_capabilities": ["fixture.capability.b"],
            },
        )
        write_yaml(
            project / ".pf" / "project-overrides.yaml",
            {
                "schema_version": 1,
                "kind": "processforge.project_overrides",
                "overrides": {
                    "specializations": [
                        {
                            "target": "fixture.specialization.a",
                            "mode": "overlay",
                            "path": ".pf/specializations/overrides/a.yaml",
                            "reason": "Fixture project overlay.",
                        }
                    ]
                },
            },
        )
        resolved = resolve_json(project, workplace, "fixture.specialization.a", process="fixture-process-a")
        if "fixture.tool.a" in resolved["activated_tools"]:
            raise AssertionError("base tool remained active after specialization overlay")
        if "fixture.tool.b" not in resolved["activated_tools"]:
            raise AssertionError("overlay tool was not activated")
        if "fixture.capability.b" not in resolved["provided_capabilities"]:
            raise AssertionError("overlay capability was not provided")
        if resolved["capability_resolution"]["unsatisfied"]:
            raise AssertionError(resolved["capability_resolution"])
        if not resolved["applied_project_overrides"]:
            raise AssertionError("specialization overlay was not recorded")
    print("PASS: smoke_project_specialization_override_applies")


if __name__ == "__main__":
    main()
