#!/usr/bin/env python3
from __future__ import annotations

import tempfile
from pathlib import Path

from core_boundary_smoke_helpers import write_project, write_workplace
from processforge import collect_project_source_inventory


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="pf-scan-workplace-") as raw:
        root = Path(raw) / "agents"
        write_project(root, project_type="agent-workspace")
        workplace_manifest = write_workplace(root / "processforge")
        (root / "project-materials").mkdir()
        (root / "project-materials" / "notes.md").write_text("project notes\n", encoding="utf-8")
        inventory = collect_project_source_inventory(root, workplace_manifest=workplace_manifest, manifest_data={"project": {"type": "agent-workspace"}})
        included = {item["path"] for item in inventory["included"]}
        excluded = {item["path"]: item for item in inventory["excluded"]}
        assert "project-materials/notes.md" in included, inventory
        assert excluded["processforge/workplace.yaml"]["role"] == "workplace_root", excluded
        assert excluded["processforge/registries/platforms.yaml"]["role"] == "workplace_root", excluded
    print("PASS: project scan excludes workplace root")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
