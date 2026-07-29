#!/usr/bin/env python3
"""Smoke process owns acceptance while specialization provides capability."""

from __future__ import annotations

import tempfile
from pathlib import Path

from specialization_smoke_helpers import read_yaml, resolve_json, write_process_with_capability, write_project, write_specialization, write_workspace


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="pf-spec-process-boundary-") as tmp:
        root = Path(tmp)
        workplace = write_workspace(root)
        write_specialization(
            workplace,
            "fixture.specialization.content",
            tool="fixture.tool.b",
            package="fixture.docs.child-content",
            provides_capabilities=["fixture.capability.a"],
        )
        project = write_project(root, workplace)
        process_path = write_process_with_capability(project)
        specialization = read_yaml(workplace / "specializations" / "fixture.specialization.content.yaml")
        process = read_yaml(process_path)
        if any(field in specialization for field in ["stages", "gates", "acceptance", "required_evidence"]):
            raise AssertionError("specialization owns workflow fields")
        stage = process["stages"][0]
        if "fixture.capability.a" not in stage.get("required_capabilities", []):
            raise AssertionError("process stage does not own capability requirement")
        if "fixture-evidence-frontend-report" not in stage.get("required_evidence", []):
            raise AssertionError("process stage does not own required evidence")
        resolved = resolve_json(project, workplace, "fixture.specialization.content", process="fixture-process-a")
        if not resolved["capability_resolution"]["satisfied"]:
            raise AssertionError("capability was not satisfied by resource profile")
    print("PASS: smoke_process_owns_acceptance_not_specialization")


if __name__ == "__main__":
    main()
