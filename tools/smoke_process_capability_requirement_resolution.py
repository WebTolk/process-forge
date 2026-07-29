#!/usr/bin/env python3
"""Smoke process capability requirements are matched against resource profiles."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

from specialization_smoke_helpers import require_ok, resolve_json, run_pf, write_process_with_capability, write_project, write_specialization, write_workspace


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="pf-spec-capability-") as tmp:
        root = Path(tmp)
        workplace = write_workspace(root)
        write_specialization(
            workplace,
            "fixture.specialization.content",
            tool="fixture.tool.b",
            package="fixture.docs.child-content",
            provides_capabilities=["fixture.capability.a"],
        )
        write_specialization(workplace, "fixture.specialization.dev", tool="fixture.tool.a", package="fixture.docs.child-dev")
        project = write_project(root, workplace)
        write_process_with_capability(project)
        satisfied = resolve_json(project, workplace, "fixture.specialization.content", process="fixture-process-a")
        if "fixture.capability.a" not in satisfied["active_resource_profile"]["provided_capabilities"]:
            raise AssertionError("resource profile did not provide expected capability")
        if not satisfied["capability_resolution"]["satisfied"] or satisfied["capability_resolution"]["unsatisfied"]:
            raise AssertionError(satisfied["capability_resolution"])
        missing_result = run_pf(
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
            "fixture.specialization.dev",
            "--json",
        )
        if missing_result.returncode == 0:
            raise AssertionError("unsatisfied capability did not fail resolution")
        payload = json.loads(missing_result.stdout)
        unsatisfied = payload["resolved_context"]["capability_resolution"]["unsatisfied"]
        if not unsatisfied or unsatisfied[0]["capability"] != "fixture.capability.a":
            raise AssertionError(missing_result.stdout)
        require_ok(run_pf("specialization-bind-platform", "--workplace", str(workplace), "--specialization", "fixture.specialization.dev", "--platform", "fixture.platform.child", "--provides-capability", "fixture.capability.a", "--apply"))
        repaired = resolve_json(project, workplace, "fixture.specialization.dev", process="fixture-process-a")
        if repaired["capability_resolution"]["unsatisfied"]:
            raise AssertionError("capability remained unsatisfied after binding update")
    print("PASS: smoke_process_capability_requirement_resolution")


if __name__ == "__main__":
    main()
