#!/usr/bin/env python3
"""Smoke-test that project .pf updates stay in assessment flow, not candidates."""

from __future__ import annotations

import json
import shutil
import tempfile
from pathlib import Path

from update_smoke_helpers import ROOT, require_ok, run_pf, write_yaml


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="pf-project-boundary-") as raw:
        project = Path(raw) / "project"
        shutil.copytree(ROOT / ".pf", project / ".pf", ignore=shutil.ignore_patterns("runtime", "artifacts", "reviews", "handoffs", "logs"))
        require_ok(run_pf("project-upgrade-check", "--project-root", str(project), "--current-version", "0.1.0", "--channel", "stable"))
        assessment = project / ".pf" / "artifacts" / "processforge-update-assessment.md"
        assert assessment.is_file()
        workplace = Path(raw) / "workplace"
        write_yaml(
            workplace / "packages" / "project-pf" / "package.yaml",
            """
id: project-local-flow
type: project_pf
version: 1.0.0
update_sites:
  - id: forbidden
    enabled: true
    manifest_url: file:///tmp/project-pf-download.json
    changelog_url: file:///tmp/project-pf-changelog.md
""",
        )
        require_ok(run_pf("update", "candidates", "refresh", "--workplace", str(workplace)))
        data = json.loads((workplace / "runtime" / "update" / "candidates.json").read_text(encoding="utf-8"))
        assert data["candidates"] == []
    print("PASS: project .pf upgrade assessment boundary smoke")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
