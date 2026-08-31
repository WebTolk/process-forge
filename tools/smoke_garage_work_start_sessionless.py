#!/usr/bin/env python3
"""Smoke test for sessionless pf.work.start."""

from smoke_garage_mode_not_promoted_by_session import call_mcp, cli

import tempfile
from pathlib import Path


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="pf-work-start-") as raw:
        root = Path(raw)
        workplace = root / "workplace"
        project = root / "project"
        cli("workplace-init", "--workplace", str(workplace), "--apply")
        cli("project-onboard", "--project-root", str(project), "--workplace", str(workplace), "--type", "generic", "--apply")
        payload = call_mcp(workplace, "pf.work.start", {"project_root": str(project), "objective": "Check project assets"})
        if payload.get("action") != "created_new" or payload.get("session", {}).get("status") != "absent":
            raise AssertionError(payload)
        if not (project / ".pf" / "runs" / str(payload["run_id"]) / "run.yaml").is_file():
            raise AssertionError(payload)
        if not (project / ".pf" / "assignments" / f"{payload['assignment_id']}.yaml").is_file():
            raise AssertionError(payload)
    print("PASS: sessionless pf.work.start creates governed work")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
