#!/usr/bin/env python3
"""Smoke-test that project .pf updates stay in assessment flow, not candidates."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

from update_smoke_helpers import require_ok, run_pf, write_yaml


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="pf-project-boundary-") as raw:
        project = Path(raw) / "project"
        write_yaml(
            project / ".pf" / "process-forge.yaml",
            """
schema_version: 1
process_forge:
  version: 0.1.0
  mode: file_only
  runner_required: false
  backend_required: false
project:
  id: example-upgrade-project
  name: Example Upgrade Project
paths:
  artifacts: artifacts
policies:
  execution_context_is_immutable: true
""",
        )
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
