#!/usr/bin/env python3
"""Smoke test that pf.work.start resolves stages from the process definition."""

from smoke_garage_mode_not_promoted_by_session import call_mcp, cli

import tempfile
from pathlib import Path


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="pf-stage-resolution-") as raw:
        root = Path(raw)
        workplace = root / "workplace"
        project = root / "project"
        cli("workplace-init", "--workplace", str(workplace), "--apply")
        cli("project-onboard", "--project-root", str(project), "--workplace", str(workplace), "--type", "generic", "--apply")
        payload = call_mcp(workplace, "pf.work.start", {"project_root": str(project), "objective": "Resolve stage automatically"})
        if payload.get("stage") != "run-intake" or payload.get("stage_selection") != "process_initial_stage":
            raise AssertionError(payload)
        invalid = call_mcp(workplace, "pf.work.start", {"project_root": str(project), "objective": "Invalid stage path", "preferred_stage": "not-a-stage"})
        if invalid.get("action") != "operator_choice_required" or "run-intake" not in invalid.get("valid_stages", []):
            raise AssertionError(invalid)
    print("PASS: pf.work.start validates and selects process stages")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
