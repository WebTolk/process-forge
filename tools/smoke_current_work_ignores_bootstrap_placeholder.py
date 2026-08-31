#!/usr/bin/env python3
"""Smoke test that first-assignment is not treated as substantive current work."""

from smoke_garage_mode_not_promoted_by_session import cli

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))

import processforge as core
from processforge_core.garage import CurrentWorkService


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="pf-current-work-") as raw:
        root = Path(raw)
        workplace = root / "workplace"
        project = root / "project"
        cli("workplace-init", "--workplace", str(workplace), "--apply")
        cli("project-onboard", "--project-root", str(project), "--workplace", str(workplace), "--type", "generic", "--apply")
        summary = CurrentWorkService(project, core).summary()
        if summary.get("governed") or summary.get("active_work"):
            raise AssertionError(summary)
    print("PASS: bootstrap first-assignment is not current substantive work")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
