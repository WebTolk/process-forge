#!/usr/bin/env python3
"""Check evolve is a generic process contract."""

from __future__ import annotations

import json

from evolve_smoke_helpers import ROOT, load_yaml


def main() -> int:
    schema = json.loads((ROOT / "schemas" / "process-definition.schema.json").read_text(encoding="utf-8"))
    if "evolve" not in schema.get("properties", {}):
        raise AssertionError("process schema has no top-level evolve")
    evolve_def = json.dumps(schema["$defs"]["evolve"])
    for forbidden in ["software-feature-development", "software", "model training"]:
        if forbidden in evolve_def:
            raise AssertionError(f"evolve schema is not generic: {forbidden}")
    non_software = []
    for process_id in ["testing", "content-production", "process-authoring", "knowledge-package-authoring"]:
        data = load_yaml(ROOT / "processes" / f"{process_id}.yaml")
        if data.get("evolve", {}).get("enabled") is True:
            non_software.append(process_id)
    if len(non_software) < 2:
        raise AssertionError("fewer than two non-software processes declare enabled evolve")
    print("PASS: evolve process-agnostic contract smoke")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
