#!/usr/bin/env python3
"""Smoke explicit session specialization switch is recorded."""

from __future__ import annotations

import tempfile
from pathlib import Path

from specialization_smoke_helpers import require_ok, run_pf, write_project, write_workspace


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="pf-spec-garage-") as tmp:
        root = Path(tmp)
        workplace = write_workspace(root)
        project = write_project(root, workplace)
        require_ok(run_pf("project-context-refresh", "--project-root", str(project), "--workplace", str(workplace)))
        output = require_ok(run_pf("session-start", "--project-root", str(project), "--mode", "resume", "--specialization", "fixture.specialization.dev", "--report-only"))
        if "SESSION:" not in output:
            raise AssertionError(output)
        telemetry_files = sorted((project / ".pf" / "runtime" / "telemetry").glob("*.ndjson"))
        if not telemetry_files or "specialization_switch" not in telemetry_files[-1].read_text(encoding="utf-8"):
            raise AssertionError("specialization switch telemetry missing")
    print("PASS: smoke_specialization_garage_mode_switch")


if __name__ == "__main__":
    main()
