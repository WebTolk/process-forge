from __future__ import annotations

import copy
import hashlib
from pathlib import Path
from typing import Any

import pytest

from processforge_core.evidence.guidance import EvidenceGuidancePolicy
from processforge_core.evidence.readiness import (
    StageReadinessPolicy,
    evidence_contract,
    evidence_matches,
)
from processforge_core.evidence.validation import EvidenceValidationService
from processforge_core.work.state import WorkStatePolicy


def validator(root: Path) -> EvidenceValidationService:
    return EvidenceValidationService(
        project_root=root,
        now_utc=lambda: "fixture-time",
        relative_path=lambda path: path.relative_to(root).as_posix(),
        sha256_file=lambda path: hashlib.sha256(path.read_bytes()).hexdigest(),
    )


def readiness(material: EvidenceValidationService) -> StageReadinessPolicy:
    return StageReadinessPolicy(
        file_diagnostic=material.diagnostic,
        string_list=lambda values: values or [],
        stage_definitions=lambda process: process.get("stages", []),
        blocker_callback=lambda code, key, item: {"code": code, key: item["id"]},
    )


def current_state() -> dict[str, Any]:
    return {
        "action": "work_incomplete",
        "stage": {"id": "build"},
        "execution_readiness": {"status": "ready"},
        "context": {"id": "assignment-capsule", "validation": {"status": "valid"}},
        "process": {"pin_status": "pinned"},
        "run": {"id": "run"},
        "assignment": {"id": "assignment"},
        "required_inputs": [{"id": "brief", "satisfied": False}],
        "artifacts": [{"id": "change", "satisfied": False}],
        "required_evidence": [{"id": "review", "satisfied": False}],
        "gates": {"entry": [], "exit": [{"id": "build-ready", "satisfied": False}]},
        "allowed_outcomes": [
            {"id": "completed", "next_stage": "verify"},
            {"id": "retry", "next_stage": "build"},
        ],
        "incomplete": [{"code": "handoff_note_required"}],
        "evidence": [],
    }


@pytest.mark.parametrize(
    "kind,kinds,keys",
    [
        ("artifact", ["artifact"], ["artifact_id", "id"]),
        ("input", ["input", "artifact"], ["input_id", "artifact_id", "id"]),
        ("evidence", ["attestation", "evidence"], ["evidence_id", "id"]),
        ("gate", ["gate"], ["gate_id", "id"]),
    ],
)
def test_contract_preserves_every_kind_and_identifier_alias(
    kind: str, kinds: list[str], keys: list[str]
) -> None:
    contract = evidence_contract(kind)
    assert contract["kinds"] == kinds and contract["id_keys"] == keys
    for record_kind in kinds:
        for key in keys:
            assert evidence_matches(
                kind, "required", {"kind": record_kind, key: "required"}
            )
    assert not evidence_matches(kind, "required", {"kind": "unknown", "id": "required"})
    assert not evidence_matches(kind, "required", {"kind": kinds[0], "id": "wrong"})
    contract["statuses"].clear()
    assert evidence_contract(kind)["statuses"]  # Callers cannot change matching rules.


def test_gate_identifier_precedence_and_requirement_alias_alternatives() -> None:
    assert not evidence_matches(
        "gate", "required", {"kind": "gate", "gate_id": "other", "id": "required"}
    )
    assert evidence_matches(
        "gate", "required", {"kind": "gate", "gate_id": "", "id": "required"}
    )
    assert evidence_matches(
        "input",
        "required",
        {"kind": "artifact", "artifact_id": "other", "id": "required"},
    )


@pytest.mark.parametrize("kind", ["input", "artifact", "evidence", "gate"])
@pytest.mark.parametrize(
    "status",
    [
        "ready",
        "present",
        "passed",
        "approved",
        "not_applicable",
        "pass",
        "failed",
        "READY",
        "",
    ],
)
def test_status_membership_and_latest_matching_record(
    kind: str, status: str, tmp_path: Path
) -> None:
    policy = readiness(validator(tmp_path))
    record = {
        "kind": evidence_contract(kind)["kinds"][0],
        "id": "required",
        "status": status,
    }
    history = [{**record, "status": "approved"}, record]
    result = (
        policy.gate({}, "required", history, phase="exit")
        if kind == "gate"
        else policy.requirement(kind, "required", history)
    )
    expected = status in (
        {"passed", "approved", "not_applicable"}
        if kind == "gate"
        else {"ready", "present", "passed", "approved", "not_applicable"}
    )
    assert result["satisfied"] is expected
    if not expected:
        assert result["diagnostic"]["code"] == "evidence_status_not_acceptable"


def test_every_generated_example_normalizes_and_satisfies_real_matcher(
    tmp_path: Path,
) -> None:
    material = validator(tmp_path)
    matcher = readiness(material)
    state = current_state()
    before = copy.deepcopy(state)
    guidance = EvidenceGuidancePolicy().project(state, process={})
    assert state == before
    assert guidance["transition_template"]["notes"].startswith("<handoff")
    assert guidance["transition_template"]["outcome"] == "<one of allowed_outcomes>"
    for requirement in guidance["requirements"]:
        for key in ("example", "not_applicable_example"):
            records, blockers = material.normalize(requirement[key])
            assert not blockers
            kind, identifier = requirement["requirement_kind"], requirement["id"]
            result = (
                matcher.gate({}, identifier, records, phase="exit")
                if kind == "gate"
                else matcher.requirement(kind, identifier, records)
            )
            assert result["satisfied"]


@pytest.mark.parametrize(
    "reason,support",
    [
        (None, ["source"]),
        (" ", ["source"]),
        ("reason", []),
        ("reason", "source"),
        ("reason", None),
    ],
)
def test_not_applicable_needs_both_reason_and_support(
    tmp_path: Path, reason: Any, support: Any
) -> None:
    records, blockers = validator(tmp_path).normalize(
        {
            "kind": "gate",
            "gate_id": "check",
            "status": "not_applicable",
            "reason": reason,
            "evidence": support,
        }
    )
    assert not records and blockers == [
        {"code": "not_applicable_evidence_incomplete", "index": 0}
    ]


def test_path_digest_diagnostics_survive_guidance_and_retry(tmp_path: Path) -> None:
    material = validator(tmp_path)
    matcher = readiness(material)
    path = tmp_path / "result.md"
    path.write_text("original", encoding="utf-8")
    records, blockers = material.normalize(
        {
            "kind": "artifact",
            "artifact_id": "change",
            "path": "result.md",
            "sha256": "caller-supplied",
        }
    )
    assert not blockers and records[0]["sha256"] != "caller-supplied"
    assert matcher.requirement("artifact", "change", records)["satisfied"]
    path.write_text("changed", encoding="utf-8")
    requirement = matcher.requirement("artifact", "change", records)
    state = current_state()
    state["artifacts"] = [requirement]
    state["evidence"] = records
    result = EvidenceGuidancePolicy().project(state, process={})
    hint = next(item for item in result["requirements"] if item["id"] == "change")
    assert hint["mismatch"]["code"] == "evidence_file_changed"
    assert not requirement["satisfied"]
    fresh, blockers = material.normalize(records)
    assert (
        not blockers and matcher.requirement("artifact", "change", fresh)["satisfied"]
    )
    for change, expected in [
        ({"sha256": ""}, "evidence_digest_missing"),
        ({"path": "missing.md"}, "evidence_file_missing"),
        ({"path": "../outside.md"}, "evidence_file_unsafe"),
        ({"path": "."}, "evidence_file_not_regular"),
    ]:
        diagnostic = material.diagnostic({**records[0], **change})
        assert diagnostic is not None and diagnostic["code"] == expected
    for invalid_path in ("missing.md", "../outside.md", ".", str(path)):
        normalized, errors = material.normalize(
            {"kind": "artifact", "id": "change", "path": invalid_path}
        )
        assert not normalized and errors[0]["code"] == "artifact_path_missing"


def test_wrong_kind_id_field_and_supplemental_evidence_are_advisory() -> None:
    state = current_state()
    state["evidence"] = [
        {"kind": "gate", "id": "change", "status": "approved"},
        {"kind": "artifact", "gate_id": "change", "status": "ready"},
        {"kind": "artifact", "id": "typo", "status": "ready"},
        {"kind": "attestation", "summary": "additional observations"},
    ]
    before = copy.deepcopy(state)
    guidance = EvidenceGuidancePolicy().project(state, process={})
    assert [item["code"] for item in guidance["unmatched_evidence"]] == [
        "kind_mismatch",
        "identifier_field_mismatch",
        "identifier_not_expected",
        "identifier_missing",
    ]
    assert state == before
    assert len(guidance["requirements"]) == 4


def test_next_gate_templates_are_conditional_and_follow_each_offered_outcome() -> None:
    state = current_state()
    state["evidence"] = [
        {"kind": "gate", "gate_id": "verify-entry", "status": "approved"}
    ]
    process = {
        "stages": [
            {"id": "verify", "entry_gates": ["verify-entry"]},
            {"id": "build", "entry_gates": ["build-entry"]},
        ],
        "gates": [],
    }
    before = copy.deepcopy(process)
    guidance = EvidenceGuidancePolicy().project(state, process=process)
    gates = guidance["conditional_next_entry_gates"]
    assert [(item["for_outcome"], item["id"]) for item in gates] == [
        ("completed", "verify-entry"),
        ("retry", "build-entry"),
    ]
    assert all(
        item["evaluation"] == "conditional_not_evaluated" and "satisfied" not in item
        for item in gates
    )
    assert not guidance["unmatched_evidence"]
    assert process == before


@pytest.mark.parametrize(
    "field,value",
    [
        ("action", "run_completed"),
        ("action", "work_terminal"),
        ("action", "work_blocked"),
        ("execution_readiness", {"status": "blocked"}),
        ("context", {"validation": {"status": "blocked"}}),
        ("process", {"pin_status": "missing"}),
        ("assignment", {"status": "done"}),
        ("assignment", {"status": "completed"}),
        ("assignment", {"status": "cancelled"}),
        ("assignment", {"status": "failed"}),
        ("run", {"status": "completed"}),
    ],
)
def test_terminal_invalid_or_blocked_work_has_no_actionable_templates(
    field: str, value: Any
) -> None:
    state = current_state()
    state[field] = value
    guidance = EvidenceGuidancePolicy().project(state, process={})
    assert not guidance["applicable"] and "transition_template" not in guidance


def test_handoff_completion_uses_notes_and_stage_attestation_when_needed() -> None:
    incomplete = WorkStatePolicy().completion_requirements(
        {
            "stage_completion": {
                "evidence_required": True,
                "handoff_note_required": True,
            }
        },
        {},
        {"stage": "build", "stage_execution": {}},
        [],
        [],
    )
    state = current_state()
    state.update(
        required_inputs=[],
        artifacts=[],
        required_evidence=[],
        gates={},
        incomplete=incomplete,
    )
    template = EvidenceGuidancePolicy().project(state, process={})[
        "transition_template"
    ]
    assert "notes" in template and template["evidence"][0]["kind"] == "attestation"
