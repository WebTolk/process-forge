from __future__ import annotations

import copy
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


def test_cli_mcp_pinned_guidance_rejections_and_recovery(scoped_work: None) -> None:
    with support.fixture() as (workplace, project, started):
        current = support.state(workplace, project)
        hints = current["evidence_guidance"]
        assert hints["applicable"]
        assert {item["id"] for item in hints["requirements"]} == {
            "brief",
            "prepare-ready",
        }
        cli_state = json.loads(
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
                str(hints["transition_template"]["context_id"]),
                "--json",
            ).stdout
        )
        assert cli_state["evidence_guidance"] == hints
        assignment_path = (
            project / ".pf" / "assignments" / f"{started['assignment_id']}.yaml"
        )
        before = assignment_path.read_bytes()
        arguments: dict[str, Any] = {
            **hints["transition_template"],
            "project_root": str(project),
        }
        arguments["evidence"] = [
            {"kind": "artifact", "artifact_id": "brief", "path": "missing.md"}
        ]
        rejected: dict[str, Any] = support.call_mcp(
            workplace, "pf.work.transition", arguments
        )
        assert rejected["action"] == "transition_rejected"
        assert (
            rejected["evidence_guidance"]["request_errors"][0]["code"]
            == "artifact_path_missing"
        )
        assert assignment_path.read_bytes() == before

        arguments["evidence"] = [
            {"kind": "gate", "gate_id": "brief", "status": "approved"}
        ]
        incomplete: dict[str, Any] = support.call_mcp(
            workplace, "pf.work.transition", arguments
        )
        assert incomplete["action"] == "incomplete"
        assert incomplete["stage"]["id"] == "prepare"
        assert (
            incomplete["evidence_guidance"]["unmatched_evidence"][0]["code"]
            == "kind_mismatch"
        )
        arguments["evidence"] = hints["transition_template"]["evidence"]
        advanced = support.call_mcp(workplace, "pf.work.transition", arguments)
        assert advanced["next_stage_id"] == "build"

        pinned_before = support.state(workplace, project)["evidence_guidance"]
        process_path = project / "processes" / "custom" / "declarative-smoke.yaml"
        changed: dict[str, Any] = copy.deepcopy(support.PROCESS)
        changed["stages"][1]["produced_artifacts"] = ["live-only-output"]
        changed["stages"][2]["entry_gates"] = ["live-only-gate"]
        process_path.write_text(json.dumps(changed), encoding="utf-8")
        assert support.state(workplace, project)["evidence_guidance"] == pinned_before
        assert (
            support.transition(workplace, project, "change", "build-ready")[
                "next_stage_id"
            ]
            == "verify"
        )
        final = support.transition(workplace, project, "report", "verify-ready")
        assert final["action"] == "run_completed"
        terminal_response: dict[str, Any] = support.call_mcp(
            workplace,
            "pf.work.state",
            {
                "project_root": str(project),
                "run_id": str(started["run_id"]),
                "assignment_id": str(started["assignment_id"]),
                "context_id": hints["transition_template"]["context_id"],
            },
        )
        terminal = terminal_response["evidence_guidance"]
        assert not terminal["applicable"] and "transition_template" not in terminal


def test_transition_only_entry_gate_is_explained_without_inventing_failure(
    monkeypatch: pytest.MonkeyPatch,
    scoped_work: None,
) -> None:
    process: dict[str, Any] = copy.deepcopy(support.PROCESS)
    process["stages"][1]["entry_gates"] = ["separate-entry"]
    process["gates"].append(
        {
            "id": "separate-entry",
            "blocking": True,
            "required": False,
            "type": "checklist",
        }
    )
    monkeypatch.setattr(support, "PROCESS", process)
    with support.fixture() as (workplace, project, _started):
        current = support.state(workplace, project)
        entries = current["evidence_guidance"]["conditional_next_entry_gates"]
        assert entries[0]["id"] == "separate-entry"
        assert entries[0]["evaluation"] == "conditional_not_evaluated"
        assert entries[0]["required_for_transition"] is True
        incomplete = support.transition(workplace, project, "brief", "prepare-ready")
        assert incomplete["action"] == "incomplete"
        assert "entry_gate_evidence_missing" in {
            item["code"] for item in incomplete["incomplete"]
        }
        assert (
            incomplete["evidence_guidance"]["conditional_next_entry_gates"] == entries
        )
        arguments: dict[str, Any] = {
            **current["evidence_guidance"]["transition_template"],
            "project_root": str(project),
        }
        arguments["evidence"].append(entries[0]["example"])
        advanced = support.call_mcp(workplace, "pf.work.transition", arguments)
        assert (
            advanced["action"] == "stage_transitioned"
            and advanced["next_stage_id"] == "build"
        )


def test_unscoped_work_reports_permissions_without_actionable_guidance() -> None:
    with support.fixture() as (workplace, project, _started):
        current = support.state(workplace, project)
        assert current["execution_readiness"]["status"] == "blocked"
        assert not current["evidence_guidance"]["applicable"]
        assert "transition_template" not in current["evidence_guidance"]
