#!/usr/bin/env python3
"""Smoke test for duplicate prevention in pf.work.start."""

from smoke_garage_mode_not_promoted_by_session import call_mcp, cli

import tempfile
from pathlib import Path


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="pf-duplicate-work-") as raw:
        root = Path(raw)
        workplace = root / "workplace"
        project = root / "project"
        cli("workplace-init", "--workplace", str(workplace), "--apply")
        cli("project-onboard", "--project-root", str(project), "--workplace", str(workplace), "--type", "generic", "--apply")
        first = call_mcp(workplace, "pf.work.start", {"project_root": str(project), "objective": "Prevent duplicate work"})
        second = call_mcp(workplace, "pf.work.start", {"project_root": str(project), "objective": "Prevent duplicate work"})
        if first.get("action") != "created_new":
            raise AssertionError(first)
        if second.get("action") != "continue_existing" or second.get("run_id") != first.get("run_id"):
            raise AssertionError({"first": first, "second": second})
    print("PASS: pf.work.start continues duplicate active work")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
