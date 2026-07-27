#!/usr/bin/env python3
"""Check knowledge candidates require explicit target/applicability metadata."""

from __future__ import annotations

import shutil
import tempfile
from pathlib import Path

from evolve_smoke_helpers import ROOT, candidate_data, init_project, run_pf, write_yaml


def main() -> int:
    schema_data = __import__("json").loads((ROOT / "schemas" / "knowledge-candidate.schema.json").read_text(encoding="utf-8"))
    required = set(schema_data.get("required", []))
    if {"source_context", "target", "applicability", "generalization"} - required:
        raise AssertionError("knowledge candidate schema does not require targeting fields")
    destination = schema_data["$defs"]["candidateDestination"]["properties"]
    if "type" not in destination or "id" not in destination:
        raise AssertionError("candidate destination schema incomplete")

    with tempfile.TemporaryDirectory(prefix="pf-evolve-targeting-schema-") as raw:
        base = Path(raw)
        project = base / "project"
        workplace = base / "workplace"
        init_project(project, workplace)

        good = project / "candidate.yaml"
        write_yaml(good, candidate_data("kc-targeting-schema-good"))
        run_pf("evolve-candidate-create", "--project-root", str(project), "--workplace", str(workplace), "--from-file", str(good))

        missing_target = candidate_data("kc-targeting-schema-missing-target")
        missing_target.pop("target")
        bad = project / "missing-target.yaml"
        write_yaml(bad, missing_target)
        run_pf("evolve-candidate-create", "--project-root", str(project), "--workplace", str(workplace), "--from-file", str(bad), expect=1)

        invalid_type = candidate_data("kc-targeting-schema-invalid-type")
        invalid_type["target"]["type"] = "global_mutation"
        bad_type = project / "invalid-type.yaml"
        write_yaml(bad_type, invalid_type)
        run_pf("evolve-candidate-create", "--project-root", str(project), "--workplace", str(workplace), "--from-file", str(bad_type), expect=1)
        shutil.rmtree(base, ignore_errors=True)

    print("PASS: evolve candidate targeting schema smoke")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
