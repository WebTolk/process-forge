#!/usr/bin/env python3
"""Ensure software lifecycle description matches represented stages."""

from __future__ import annotations

from pathlib import Path

import yaml  # type: ignore


ROOT = Path(__file__).resolve().parents[1]
PROCESS = ROOT / "examples" / "domain-packs" / "software-web" / "processes" / "software-feature-development.yaml"


def main() -> int:
    data = yaml.safe_load(PROCESS.read_text(encoding="utf-8"))
    description = data["description"].lower()
    stages = {stage["id"] for stage in data["stages"]}
    artifacts = {item["id"] for item in data["artifact_definitions"]}
    assert "release" in description
    assert "evolution" in description or "evolve" in description
    assert "release-delivery" in stages
    assert "evolve" in stages
    assert {"release-notes", "delivery-report", "evolution-report"} <= artifacts
    assert "release and evolution" not in description or {"release-delivery", "evolve"} <= stages
    print("PASS: software lifecycle description alignment smoke")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
