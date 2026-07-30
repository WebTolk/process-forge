#!/usr/bin/env python3
"""Check software lifecycle uses the common evolve contract."""

from __future__ import annotations

from evolve_smoke_helpers import ROOT, load_yaml


def main() -> int:
    pack_root = ROOT / "packs" / "official"
    process = load_yaml(pack_root / "software-development" / "processes" / "software-feature-development.yaml")
    evolve = process.get("evolve")
    if not isinstance(evolve, dict):
        raise AssertionError("software process missing top-level evolve")
    targets = set(evolve.get("candidate_targets") or [])
    expected = {"knowledge_package", "delivery_profile", "process_definition", "project_rule", "platform_contract"}
    if targets != expected:
        raise AssertionError(f"software process target set mismatch: {sorted(targets)}")
    testing_targets = set(load_yaml(pack_root / "verification" / "processes" / "testing.yaml").get("evolve", {}).get("candidate_targets") or [])
    if "regression_check" not in testing_targets:
        raise AssertionError("testing process must route test gaps to regression_check")
    targeting = evolve.get("candidate_targeting") if isinstance(evolve.get("candidate_targeting"), dict) else {}
    if targeting.get("require_target") is not True or targeting.get("default_to_narrowest_scope") is not True:
        raise AssertionError("software process does not use common candidate targeting requirements")
    if "software_only" in str(evolve).lower():
        raise AssertionError("software process evolve is marked software-only")
    print("PASS: software process uses common evolve smoke")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
