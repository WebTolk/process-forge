#!/usr/bin/env python3
"""Regression smoke for root and derived platform selection during onboarding."""

from __future__ import annotations

import tempfile
from pathlib import Path

import yaml

from core_boundary_smoke_helpers import write_workplace
from smoke_domain_neutral_core_helpers import load_processforge


def write_contract(path: Path, contract_id: str, *, project_type: str = "fixture-extension", derived: bool = False, detection_directory: str = "") -> None:
    extends = "" if not derived else """extends:
  - id: platform.example
    required: true
"""
    detection = "" if not detection_directory else f"""detection:
  directories:
    any:
      - {detection_directory}
"""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        f"""schema_version: 1
id: platform.{contract_id}
title: {contract_id}
type: platform_contract
version: 1.0.0
project_type_hints:
  - {project_type}
{extends}{detection}requires:
  capabilities: []
  knowledge_packages: []
  tools: []
  mcp: []
  templates: []
includes:
  knowledge_packages: []
  tools: []
  mcp: []
  templates: []
""",
        encoding="utf-8",
    )


def write_fixture_workplace(root: Path) -> Path:
    workplace_manifest = write_workplace(root)
    contracts_root = root / "platform-contracts"
    write_contract(contracts_root / "platform.example" / "platform-contract.yaml", "example")
    write_contract(contracts_root / "platform.example-child-explicit" / "platform-contract.yaml", "example-child-explicit", derived=True)
    write_contract(contracts_root / "platform.example-child-detected" / "platform-contract.yaml", "example-child-detected", derived=True, detection_directory="fixture-child-marker")
    write_contract(contracts_root / "platform.example-child-classified" / "platform-contract.yaml", "example-child-classified", derived=True)
    write_contract(contracts_root / "platform.example-child-specific" / "platform-contract.yaml", "example-child-specific", project_type="fixture-specific-extension", derived=True)
    (root / "registries" / "platforms.yaml").write_text(
        """schema_version: 1
platforms:
  - id: example
    package_id: platform.example
    path: platform-contracts/platform.example/platform-contract.yaml
    status: available
  - id: example-child-explicit
    package_id: platform.example-child-explicit
    path: platform-contracts/platform.example-child-explicit/platform-contract.yaml
    status: available
  - id: example-child-detected
    package_id: platform.example-child-detected
    path: platform-contracts/platform.example-child-detected/platform-contract.yaml
    status: available
  - id: example-child-classified
    package_id: platform.example-child-classified
    path: platform-contracts/platform.example-child-classified/platform-contract.yaml
    status: available
  - id: example-child-specific
    package_id: platform.example-child-specific
    path: platform-contracts/platform.example-child-specific/platform-contract.yaml
    status: available
""",
        encoding="utf-8",
    )
    return workplace_manifest


def selected(pf: object, project: Path, workplace: Path, *, project_type: str = "fixture-extension", detected: list[str] | None = None, answers: dict[str, object] | None = None) -> list[str]:
    return pf.selected_project_platforms(
        {"platforms": detected or []},
        answers or {"project": {}},
        project_type,
        workplace,
        project,
    )


def main() -> int:
    pf = load_processforge()
    with tempfile.TemporaryDirectory(prefix="pf-platform-onboard-selection-") as raw:
        root = Path(raw)
        workplace = write_fixture_workplace(root / "workplace")

        generic_project = root / "generic"
        generic_project.mkdir()
        automatic = selected(pf, generic_project, workplace)
        assert automatic == ["example"], automatic
        generated = pf.build_project_files(generic_project, workplace, {"project": {"type": "fixture-extension"}})
        manifest = yaml.safe_load(generated[generic_project / ".pf" / "process-forge.yaml"])
        assert [item["id"] for item in manifest["platform_contracts"]] == ["platform.example"], manifest["platform_contracts"]

        explicit_project = root / "explicit"
        explicit_project.mkdir()
        explicit = selected(pf, explicit_project, workplace, answers={"project": {"platform": "example-child-explicit"}})
        assert explicit == ["example", "example-child-explicit"], explicit

        detected_project = root / "detected"
        (detected_project / "fixture-child-marker").mkdir(parents=True)
        detected = selected(pf, detected_project, workplace)
        assert detected == ["example", "example-child-detected"], detected

        classified_project = root / "classified"
        classified_project.mkdir()
        classified = selected(pf, classified_project, workplace, detected=["example-child-classified"])
        assert classified == ["example", "example-child-classified"], classified

        specific_project = root / "specific"
        specific_project.mkdir()
        specific = selected(pf, specific_project, workplace, project_type="fixture-specific-extension")
        assert specific == ["example-child-specific"], specific
    print("PASS: project onboarding selects derived platforms only with evidence")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
