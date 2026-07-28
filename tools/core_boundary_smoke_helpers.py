#!/usr/bin/env python3
"""Helpers for core boundary scan guard smokes."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))


def write_project(project: Path, *, project_type: str = "software-project", detected_platforms: list[str] | None = None) -> Path:
    flow = project / ".pf"
    flow.mkdir(parents=True, exist_ok=True)
    detected = ""
    if detected_platforms:
        detected = "\n".join(["detected:", "  platforms:", *[f"    - {item}" for item in detected_platforms], ""])
    (flow / "process-forge.yaml").write_text(
        f"""schema_version: 1
project:
  id: smoke
  type: {project_type}
workplace:
  reference: auto
process_forge:
  version: 1.0.0
{detected}""",
        encoding="utf-8",
    )
    return flow


def write_workplace(workplace: Path) -> Path:
    (workplace / "registries").mkdir(parents=True, exist_ok=True)
    (workplace / "platform-contracts" / "platform.example").mkdir(parents=True, exist_ok=True)
    (workplace / "workplace.yaml").write_text(
        """schema_version: 1
registries:
  platforms: registries/platforms.yaml
  knowledge_roots: registries/knowledge-roots.yaml
  package_roots: registries/package-roots.yaml
""",
        encoding="utf-8",
    )
    (workplace / "registries" / "platforms.yaml").write_text(
        """schema_version: 1
platforms:
  - id: example
    package_id: platform.example
    path: platform-contracts/platform.example/platform-contract.yaml
    status: available
""",
        encoding="utf-8",
    )
    (workplace / "registries" / "knowledge-roots.yaml").write_text("schema_version: 1\nknowledge_roots: []\n", encoding="utf-8")
    (workplace / "registries" / "package-roots.yaml").write_text("schema_version: 1\npackage_roots: []\n", encoding="utf-8")
    (workplace / "platform-contracts" / "platform.example" / "platform-contract.yaml").write_text(
        """schema_version: 1
id: platform.example
title: Example
type: platform_contract
version: 1.0.0
status: draft
project_type_hints:
  - example-extension
applies_to:
  platforms:
    - example
requires:
  capabilities: []
  knowledge_packages: []
  tools: []
  mcp: []
  templates: []
""",
        encoding="utf-8",
    )
    return workplace / "workplace.yaml"


def write_pf_distribution(root: Path) -> Path:
    (root / "bin").mkdir(parents=True, exist_ok=True)
    (root / "tools").mkdir(parents=True, exist_ok=True)
    (root / "schemas").mkdir(parents=True, exist_ok=True)
    (root / "processes" / "core").mkdir(parents=True, exist_ok=True)
    (root / "bin" / "pf.py").write_text("# smoke\n", encoding="utf-8")
    (root / "tools" / "processforge.py").write_text("# smoke\n", encoding="utf-8")
    (root / "schemas" / "process-definition.schema.json").write_text("{}\n", encoding="utf-8")
    (root / "processes" / "core" / "software-feature-development.yaml").write_text("id: software-feature-development\n", encoding="utf-8")
    return root
