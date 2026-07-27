#!/usr/bin/env python3
"""Check process-authoring asks for explicit common evolve decisions."""

from __future__ import annotations

import json

from evolve_smoke_helpers import ROOT


def main() -> int:
    answers_schema = json.loads((ROOT / "schemas" / "process-authoring-answers.schema.json").read_text(encoding="utf-8"))
    if "evolve" not in answers_schema.get("required", []):
        raise AssertionError("answers schema does not require evolve")
    evolve = answers_schema["properties"]["evolve"]
    if "decision" not in evolve.get("required", []):
        raise AssertionError("answers schema does not require evolve.decision")
    if "reason" not in evolve["properties"]["decision"].get("required", []):
        raise AssertionError("disabled evolve reason is not required in decision")
    template = (ROOT / "templates" / "process-authoring-answers.yaml").read_text(encoding="utf-8")
    prompt = (ROOT / "prompts" / "process-authoring-agent.md").read_text(encoding="utf-8")
    for needle in ["evolve:", "decision:", "candidate_targets:", "candidate_targeting:", "ask_target_layer: true", "export_requires_sanitization: true"]:
        if needle not in template:
            raise AssertionError(f"template missing {needle}")
    for needle in ["explicit common `evolve` decision", "Do not generate", "process-agnostic", "target layer", "narrowest safe scope", "LLM model training"]:
        if needle not in prompt:
            raise AssertionError(f"prompt missing {needle}")
    print("PASS: process-authoring evolve questions smoke")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
