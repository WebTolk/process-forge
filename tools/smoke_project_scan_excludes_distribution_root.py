#!/usr/bin/env python3
from __future__ import annotations

import tempfile
from pathlib import Path

from core_boundary_smoke_helpers import write_pf_distribution, write_project
from processforge import collect_project_source_inventory


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="pf-scan-dist-") as raw:
        root = Path(raw) / "agents"
        project = root
        write_project(project, project_type="agent-workspace")
        distribution = write_pf_distribution(root / "processforge")
        (root / "project-materials").mkdir()
        (root / "project-materials" / "notes.md").write_text("project notes\n", encoding="utf-8")
        inventory = collect_project_source_inventory(project, distribution_root=distribution, manifest_data={"project": {"type": "agent-workspace"}})
        included = {item["path"] for item in inventory["included"]}
        excluded = {item["path"]: item for item in inventory["excluded"]}
        assert "project-materials/notes.md" in included, inventory
        assert excluded["processforge/bin/pf.py"]["role"] == "distribution_root", excluded
        assert excluded["processforge/tools/processforge.py"]["role"] == "distribution_root", excluded
    print("PASS: project scan excludes distribution root")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
