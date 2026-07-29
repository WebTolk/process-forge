#!/usr/bin/env python3
from __future__ import annotations

import tempfile
from pathlib import Path

from core_boundary_smoke_helpers import write_project, write_workplace
from processforge import build_project_context_snapshot


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="pf-platform-snapshot-") as raw:
        base = Path(raw)
        workplace_manifest = write_workplace(base / "workplace")

        agent_project = base / "agent-workspace"
        write_project(agent_project, project_type="agent-workspace")
        agent_snapshot = build_project_context_snapshot(agent_project, explicit_workplace=str(workplace_manifest.parent))
        assert agent_snapshot["available_platform_contracts"], agent_snapshot
        assert agent_snapshot["selected_platform_contracts"] == [], agent_snapshot["selected_platform_contracts"]
        assert agent_snapshot["platform_stack"] == [], agent_snapshot["platform_stack"]
        assert agent_snapshot["platform_selection"]["status"] == "not_applicable", agent_snapshot["platform_selection"]

        example_project = base / "example-extension"
        example_flow = write_project(example_project, project_type="example-extension")
        manifest = example_flow / "process-forge.yaml"
        manifest.write_text(
            manifest.read_text(encoding="utf-8")
            + """platform_contracts:
  - id: platform.example
    platform: example
""",
            encoding="utf-8",
        )
        example_snapshot = build_project_context_snapshot(example_project, explicit_workplace=str(workplace_manifest.parent))
        assert any(item["id"] == "platform.example" for item in example_snapshot["selected_platform_contracts"]), example_snapshot["selected_platform_contracts"]
        assert any(item["id"] == "platform.example" for item in example_snapshot["platform_stack"]), example_snapshot["platform_stack"]
    print("PASS: agent workspace platform availability snapshot")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
