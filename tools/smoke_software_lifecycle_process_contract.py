#!/usr/bin/env python3
"""Validate the software-feature-development lifecycle contract."""

from __future__ import annotations

from pathlib import Path

import yaml  # type: ignore


ROOT = Path(__file__).resolve().parents[1]
PROCESS = ROOT / "processes" / "core" / "software-feature-development.yaml"


def main() -> int:
    data = yaml.safe_load(PROCESS.read_text(encoding="utf-8"))
    assert data["id"] == "software-feature-development"
    stages = [stage["id"] for stage in data["stages"]]
    expected = [
        "orchestration",
        "intake-scope",
        "investigation",
        "domain-modeling",
        "architecture-plan",
        "implementation",
        "code-assurance",
        "release-delivery",
        "evolve",
    ]
    positions = [stages.index(stage_id) for stage_id in expected]
    assert positions == sorted(positions), stages
    for stage_id in expected:
        assert stage_id in stages
    assert "release-delivery" in stages
    assert "evolve" in stages
    assert data.get("execution_mode") == "single_agent"
    assert data.get("coordination_requirements", {}).get("mode") == "simple_allowed"
    assert data.get("error_handling", {}).get("mode") == "none"
    assert data.get("metadata", {}).get("lifecycle_modes", {})
    print("PASS: software lifecycle process contract smoke")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
