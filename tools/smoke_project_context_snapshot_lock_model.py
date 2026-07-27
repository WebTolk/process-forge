#!/usr/bin/env python3
from __future__ import annotations

import tempfile
from pathlib import Path

from context_lock_smoke_helpers import make_assignment, make_project, refresh, require_ok, run_pf, snapshot


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="pf-context-lock-") as raw:
        project = make_project(Path(raw))
        refresh(project)
        snap = snapshot(project)
        assert snap["context_requirements"]["knowledge_resources"]
        resources = snap["resolved"]["knowledge_resources"]
        assert any(item["id"] == "docs-joomla:joomla-core" and item["instance_id"] == "docs-joomla:joomla-core@5.4.5" for item in resources)
        assert any(item["id"] == "docs-joomla:joomla-development-articles" and item["resolved_generation"] == "A" for item in resources)
        assignment = make_assignment(project)
        require_ok(run_pf("assignment-capsule", "--project-root", str(project), "--assignment", str(assignment)))
        capsule_text = (project / ".pf" / "contexts" / "assignment-capsules" / "demo-task.capsule.yaml").read_text(encoding="utf-8")
        assert "context_snapshot:" in capsule_text
        assert "latest" not in capsule_text.lower()
    print("PASS: project context snapshot lock model smoke")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
