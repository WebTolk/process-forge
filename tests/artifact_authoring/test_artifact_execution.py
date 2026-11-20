from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import process_execution_smoke_support as support
import pytest


@pytest.fixture
def scoped_work(monkeypatch: pytest.MonkeyPatch) -> None:
    original = support.call_mcp

    def call(
        workplace: Path, name: str, arguments: dict[str, object]
    ) -> dict[str, object]:
        if name == "pf.work.start":
            arguments = {
                **arguments,
                "scope_intent": {
                    "schema_version": 1,
                    "assignment": {
                        "allowed_actions": ["read", "write_artifact", "write_product"],
                        "allowed_read_files": ["**"],
                        "allowed_files": ["results/**", ".pf/artifacts/**"],
                        "ownership": {"owner_id": "fixture-agent", "writer": True},
                        "execution_mode": {
                            "kind": "implementation",
                            "code_changes_allowed": True,
                            "artifact_changes_allowed": True,
                        },
                    },
                },
            }
        return original(workplace, name, arguments)

    monkeypatch.setattr(support, "call_mcp", call)


def test_authoring_warnings_survive_real_transition_and_do_not_rewrite_history(
    scoped_work: None,
) -> None:
    with support.fixture() as (workplace, project, started):
        current = support.state(workplace, project)
        assert current["authoring_review"]["current_stage"]["status"] == "not_recorded"
        artifact = project / ".pf/artifacts/brief.md"
        artifact.parent.mkdir(exist_ok=True)
        original = b"# Report\n\xffunreadable\n"
        artifact.write_bytes(original)
        args = {
            **current["evidence_guidance"]["transition_template"],
            "project_root": str(project),
        }
        args["evidence"][0]["path"] = ".pf/artifacts/brief.md"
        advanced: dict[str, Any] = support.call_mcp(
            workplace, "pf.work.transition", args
        )
        assert advanced["action"] == "stage_transitioned"
        group = advanced["authoring_review"]["last_completed_stage"]
        assert group["stage_id"] == "prepare"
        assert group["entries"][0]["review"]["findings"][0]["code"] == "invalid_utf8"
        assert artifact.read_bytes() == original
        cli = json.loads(
            support.cli(
                "work-state",
                "--project-root",
                str(project),
                "--workplace",
                str(workplace),
                "--run",
                str(started["run_id"]),
                "--assignment",
                str(started["assignment_id"]),
                "--context-id",
                args["context_id"],
                "--json",
            ).stdout
        )
        assert cli["authoring_review"] == advanced["authoring_review"]
        history = support.assignment(project, started)["stage_history"]
        old_evidence = history[0]["evidence"]
        artifact.write_text(
            "# Report\nReviewed server change; no UI files changed.\n", encoding="utf-8"
        )
        changed = support.state(workplace, project)
        assert changed["authoring_review"]["last_completed_stage"] == group
        assert (
            changed["required_inputs"][0]["diagnostic"]["code"]
            == "evidence_file_changed"
        )
        assert (
            support.assignment(project, started)["stage_history"][0]["evidence"]
            == old_evidence
        )
        build_args = {
            **args,
            "evidence": [
                {
                    "kind": "artifact",
                    "artifact_id": "brief",
                    "path": ".pf/artifacts/brief.md",
                },
                {
                    "kind": "artifact",
                    "artifact_id": "change",
                    "path": ".pf/artifacts/brief.md",
                },
                {
                    "kind": "gate",
                    "gate_id": "build-ready",
                    "status": "not_applicable",
                    "reason": "N/A",
                    "evidence": ["reviewed-diff"],
                },
            ],
        }
        built: dict[str, Any] = support.call_mcp(
            workplace, "pf.work.transition", build_args
        )
        assert built["action"] == "stage_transitioned"
        assert (
            built["authoring_review"]["last_completed_stage"]["entries"][-1]["review"][
                "findings"
            ][0]["code"]
            == "generic_not_applicable"
        )
        final = support.transition(workplace, project, "report", "verify-ready")
        assert final["action"] == "run_completed"
