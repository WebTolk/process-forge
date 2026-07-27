#!/usr/bin/env python3
"""Check knowledge candidate schema and CLI sanitizer surface."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

from evolve_smoke_helpers import ROOT, candidate_data, run_pf, write_yaml


def main() -> int:
    schema = json.loads((ROOT / "schemas" / "knowledge-candidate.schema.json").read_text(encoding="utf-8"))
    if schema["properties"]["kind"].get("const") != "processforge.knowledge_candidate":
        raise AssertionError("knowledge candidate schema kind mismatch")
    target = schema["properties"]["target"]
    if "$ref" not in target:
        raise AssertionError("knowledge candidate target must be an object reference")
    targets = set(schema["$defs"]["candidateDestination"]["properties"]["type"]["enum"])
    if {"knowledge_package", "template_package", "process_definition", "platform_contract", "project_rule"} - targets:
        raise AssertionError("candidate target enum incomplete")
    with tempfile.TemporaryDirectory(prefix="pf-candidate-schema-") as raw:
        path = Path(raw) / "candidate.yaml"
        write_yaml(path, candidate_data())
        run_pf("evolve-candidate-sanitize", "--file", str(path))
        if not path.with_name("candidate.sanitized.yaml").is_file():
            raise AssertionError("sanitized candidate was not written")
    print("PASS: evolve candidate schema smoke")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
