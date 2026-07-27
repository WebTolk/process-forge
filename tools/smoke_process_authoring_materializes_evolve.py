#!/usr/bin/env python3
"""Check process-authoring materializes enabled and disabled evolve blocks."""

from __future__ import annotations

import shutil
import tempfile
from pathlib import Path

from evolve_smoke_helpers import ROOT, init_project, load_yaml, run_pf, write_yaml


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="pf-authoring-evolve-") as raw:
        base = Path(raw)
        project = base / "project"
        workplace = base / "workplace"
        init_project(project, workplace)
        answers = project / "answers.yaml"
        shutil.copyfile(ROOT / "examples" / "process-authoring" / "single-agent-simple" / "answers.yaml", answers)
        run_pf("process-create", "--project-root", str(project), "--answers", str(answers), "--apply")
        process_id = load_yaml(answers)["process"]["id"]
        process = load_yaml(project / "processes" / f"{process_id}.yaml")
        evolve = process.get("evolve", {})
        assert evolve["enabled"] is True
        assert evolve["mode"] == "optional"
        assert evolve["timing"] == "end_of_run"
        assert "knowledge_package" in evolve["candidate_targets"]
        assert evolve["candidate_targeting"]["require_target"] is True
        assert evolve["candidate_targeting"]["require_applicability"] is True
        assert evolve["candidate_targeting"]["default_to_narrowest_scope"] is True
        assert evolve["privacy"]["export_requires_sanitization"] is True
        assert evolve["apply_policy"]["auto_apply_global"] is False

        disabled = load_yaml(answers)
        disabled["process"]["id"] = "disabled-evolve-process"
        disabled["process"]["name"] = "Disabled Evolve Process"
        disabled["evolve"] = {"enabled": False, "decision": {"value": "disabled", "reason": "Administrative registration process."}, "mode": "disabled"}
        disabled_answers = project / "disabled.answers.yaml"
        write_yaml(disabled_answers, disabled)
        run_pf("process-create", "--project-root", str(project), "--answers", str(disabled_answers), "--apply")
        disabled_process = load_yaml(project / "processes" / "disabled-evolve-process.yaml")
        assert disabled_process["evolve"]["enabled"] is False
        assert disabled_process["evolve"]["mode"] == "disabled"
        assert disabled_process["evolve"]["decision"]["reason"]
    print("PASS: process-authoring materializes evolve smoke")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
