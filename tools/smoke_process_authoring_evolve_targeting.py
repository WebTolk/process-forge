#!/usr/bin/env python3
"""Check process authoring asks for and materializes evolve candidate targeting."""

from __future__ import annotations

import json
import shutil
import tempfile
from pathlib import Path

from evolve_smoke_helpers import ROOT, init_project, load_yaml, run_pf


def main() -> int:
    schema = json.loads((ROOT / "schemas" / "process-authoring-answers.schema.json").read_text(encoding="utf-8"))
    evolve = schema["properties"]["evolve"]["properties"]
    if "candidate_targeting" not in evolve:
        raise AssertionError("answers schema missing candidate_targeting")

    template = (ROOT / "templates" / "process-authoring-answers.yaml").read_text(encoding="utf-8")
    prompt = (ROOT / "prompts" / "process-authoring-agent.md").read_text(encoding="utf-8")
    for needle in ["ask_target_layer: true", "ask_applicability: true", "ask_not_applicable: true", "ask_generalization_level: true"]:
        if needle not in template:
            raise AssertionError(f"template missing {needle}")
    for needle in ["target layer", "where the observation applies", "narrowest safe scope"]:
        if needle not in prompt:
            raise AssertionError(f"prompt missing {needle}")

    with tempfile.TemporaryDirectory(prefix="pf-authoring-targeting-") as raw:
        base = Path(raw)
        project = base / "project"
        workplace = base / "workplace"
        init_project(project, workplace)
        answers = project / "answers.yaml"
        shutil.copyfile(ROOT / "templates" / "process-authoring-answers.yaml", answers)
        run_pf("process-create", "--project-root", str(project), "--answers", str(answers), "--apply")
        process_id = load_yaml(answers)["process"]["id"]
        process = load_yaml(project / "processes" / "user" / f"{process_id}.yaml")
        targeting = process["evolve"]["candidate_targeting"]
        if targeting.get("require_target") is not True or targeting.get("require_applicability") is not True:
            raise AssertionError(targeting)
        if targeting.get("default_to_narrowest_scope") is not True:
            raise AssertionError(targeting)

    print("PASS: process authoring evolve targeting smoke")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
