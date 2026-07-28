#!/usr/bin/env python3
from __future__ import annotations

import tempfile
from pathlib import Path

from core_boundary_smoke_helpers import write_project
from processforge import build_project_context_snapshot, project_knowledge_resource_index_checks


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="pf-project-package-index-") as raw:
        project = Path(raw)
        flow = write_project(project, project_type="software-project")
        manifest = flow / "process-forge.yaml"
        manifest.write_text(
            manifest.read_text(encoding="utf-8")
            + """packages:
  - id: project.example
    path: packages/project.example.yaml
""",
            encoding="utf-8",
        )
        (flow / "packages" / "project.example" / "resources").mkdir(parents=True)
        (flow / "packages" / "project.example" / "resources" / "note.md").write_text("note\n", encoding="utf-8")
        (flow / "packages" / "project.example.yaml").write_text(
            """schema_version: 1
id: project.example
type: knowledge_package
resources:
  - id: note
    kind: reference
    path_ref:
      package: project.example
      relative_path: resources/note.md
""",
            encoding="utf-8",
        )
        checks = project_knowledge_resource_index_checks(project, None, None)
        messages = "\n".join(item.message for item in checks)
        assert "knowledge resource index for project.example missing" not in messages, messages
        assert "optional for project-local package resources" in messages, messages
        snapshot = build_project_context_snapshot(project)
        resources = snapshot["resolved"]["available_knowledge_resources"]
        assert any(item.get("package_id") == "project.example" and item.get("id") == "project.example:note" for item in resources), resources
    print("PASS: project-local package index detection")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
