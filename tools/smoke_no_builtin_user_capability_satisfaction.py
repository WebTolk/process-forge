#!/usr/bin/env python3
"""Smoke missing user capability is never satisfied by ProcessForge core."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

from specialization_smoke_helpers import run_pf, write_process_with_capability, write_project, write_specialization, write_workspace


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="pf-no-builtin-cap-") as tmp:
        root = Path(tmp)
        workplace = write_workspace(root)
        write_specialization(workplace, "fixture.specialization.empty")
        project = write_project(root, workplace)
        write_process_with_capability(project, capability="fixture.capability.missing")
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
            raise AssertionError("missing capability resolved successfully")
        payload = json.loads(result.stdout)
        resolved = payload["resolved_context"]
        unsatisfied = resolved["capability_resolution"]["unsatisfied"]
        if resolved.get("status") != "needs_resources":
            raise AssertionError(result.stdout)
        if not unsatisfied or unsatisfied[0].get("capability") != "fixture.capability.missing":
            raise AssertionError(result.stdout)
        for item in resolved["capability_resolution"]["satisfied"]:
            provider = item.get("satisfied_by") if isinstance(item, dict) else {}
            if isinstance(provider, dict) and provider.get("provider") == "builtin":
                raise AssertionError(result.stdout)
    print("PASS: smoke_no_builtin_user_capability_satisfaction")


if __name__ == "__main__":
    main()
