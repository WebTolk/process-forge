#!/usr/bin/env python3
"""Smoke capability resolution depends on workspace data only."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

from specialization_smoke_helpers import resolve_json, run_pf, write_process_with_capability, write_project, write_specialization, write_workspace


def assert_unsatisfied(project: Path, workplace: Path) -> None:
    result = run_pf(
        "context-resolve",
        "--project-root",
        str(project),
        "--workplace",
        str(workplace),
        "--platform",
        "fixture.platform.child",
        "--process",
        "fixture-process-a",
        "--specialization",
        "fixture.specialization.empty",
        "--json",
    )
    if result.returncode == 0:
        raise AssertionError("workspace without provider satisfied fixture.capability.a")
    resolved = json.loads(result.stdout)["resolved_context"]
    if not resolved["capability_resolution"]["unsatisfied"]:
        raise AssertionError(result.stdout)


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="pf-data-driven-cap-") as tmp:
        root = Path(tmp)

        workplace_a = write_workspace(root / "a")
        write_specialization(workplace_a, "fixture.specialization.a", provides_capabilities=["fixture.capability.a"])
        project_a = write_project(root / "a", workplace_a)
        write_process_with_capability(project_a)
        resolved_a = resolve_json(project_a, workplace_a, "fixture.specialization.a", process="fixture-process-a")
        if not resolved_a["capability_resolution"]["satisfied"] or resolved_a["capability_resolution"]["unsatisfied"]:
            raise AssertionError(resolved_a["capability_resolution"])

        workplace_b = write_workspace(root / "b")
        write_specialization(workplace_b, "fixture.specialization.empty")
        project_b = write_project(root / "b", workplace_b)
        write_process_with_capability(project_b)
        assert_unsatisfied(project_b, workplace_b)
    print("PASS: smoke_capability_resolution_data_driven_only")


if __name__ == "__main__":
    main()
