#!/usr/bin/env python3
"""Validate compact lifecycle and not_applicable policy."""

from __future__ import annotations

from pathlib import Path

import yaml  # type: ignore


ROOT = Path(__file__).resolve().parents[1]
PROCESS = ROOT / "processes" / "software-feature-development.yaml"


def main() -> int:
    data = yaml.safe_load(PROCESS.read_text(encoding="utf-8"))
    metadata = data.get("metadata", {})
    modes = metadata.get("lifecycle_modes", {})
    assert {"feature", "bug_fix", "debug_loop", "implementation_only"} <= set(modes)
    assert metadata.get("compact_mode", {}).get("allowed") is True
    stages = {stage["id"]: stage for stage in data["stages"]}
    for stage_id in ("release-delivery", "evolve"):
        stage = stages[stage_id]
        assert stage.get("conditional") is True
        policy = stage.get("not_applicable_policy", {})
        assert policy.get("required") is True
        assert set(policy.get("evidence_fields", [])) >= {"status", "reason", "evidence"}
    gates = {gate["id"]: gate for gate in data["gates"]}
    assert gates["release-readiness-decided"].get("not_applicable_example", {}).get("status") == "not_applicable"
    assert "evolution-report" in stages["evolve"].get("produced_artifacts", [])
    print("PASS: software lifecycle compact mode smoke")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

