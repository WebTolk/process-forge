#!/usr/bin/env python3
from __future__ import annotations

import tempfile
from pathlib import Path

from core_boundary_smoke_helpers import write_project
from processforge import collect_project_source_inventory


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="pf-scan-knowledge-") as raw:
        root = Path(raw) / "agents"
        write_project(root, project_type="agent-workspace")
        (root / "docs" / "joomla").mkdir(parents=True)
        (root / "docs" / "joomla" / "index.md").write_text("docs\n", encoding="utf-8")
        (root / "project-materials").mkdir()
        (root / "project-materials" / "notes.md").write_text("project notes\n", encoding="utf-8")
        manifest = {"project": {"type": "agent-workspace"}, "knowledge_roots": [{"id": "local-docs", "path": "docs"}]}
        inventory = collect_project_source_inventory(root, manifest_data=manifest)
        included = {item["path"] for item in inventory["included"]}
        excluded = {item["path"]: item for item in inventory["excluded"]}
        assert "project-materials/notes.md" in included, inventory
        assert excluded["docs/joomla/index.md"]["role"] == "knowledge_root", excluded
    print("PASS: project scan excludes knowledge roots")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
