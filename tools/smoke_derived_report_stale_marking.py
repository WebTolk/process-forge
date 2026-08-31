#!/usr/bin/env python3
"""Smoke test for derived report stale markers in pf.context."""

from smoke_garage_mode_not_promoted_by_session import call_mcp, cli

import os
import tempfile
from pathlib import Path


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="pf-derived-report-") as raw:
        root = Path(raw)
        workplace = root / "workplace"
        project = root / "project"
        cli("workplace-init", "--workplace", str(workplace), "--apply")
        cli("project-onboard", "--project-root", str(project), "--workplace", str(workplace), "--type", "generic", "--apply")
        report = project / ".pf" / "artifacts" / "project-profile.md"
        os.utime(report, (1, 1))
        context = call_mcp(workplace, "pf.context", {"project_root": str(project)})
        reports = context.get("derived_reports", {}).get("reports", [])
        profile = next((item for item in reports if item.get("path") == ".pf/artifacts/project-profile.md"), {})
        if profile.get("status") != "stale":
            raise AssertionError(context.get("derived_reports"))
    print("PASS: pf.context marks stale derived reports")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
