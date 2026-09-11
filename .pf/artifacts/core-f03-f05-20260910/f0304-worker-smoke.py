#!/usr/bin/env python3
"""Regression smoke for latest evidence selection and saved-file freshness.

The fixture is deliberately driven through the ordinary MCP Work surface.  It
uses only temporary PF projects, so the smoke remains runnable from an
extracted distribution without repository-private evidence.
"""

from __future__ import annotations

from pathlib import Path

import yaml

from processforge_core.process_execution import canonical_fingerprint
from process_execution_smoke_support import assignment, call_mcp, fixture, run, state, transition


def require(condition: bool, payload: object) -> None:
    if not condition:
        raise AssertionError(payload)


def evidence(*items: dict[str, str]) -> list[dict[str, str]]:
    return list(items)


def artifact(identifier: str, status: str = "ready", **extra: str) -> dict[str, str]:
    return {"kind": "artifact", "artifact_id": identifier, "status": status, **extra}


def input_evidence(identifier: str, status: str = "ready", **extra: str) -> dict[str, str]:
    return {"kind": "input", "input_id": identifier, "status": status, **extra}


def gate(identifier: str, status: str = "passed", **extra: str) -> dict[str, str]:
    return {"kind": "gate", "gate_id": identifier, "status": status, **extra}


def build_evidence(*extra: dict[str, str]) -> list[dict[str, str]]:
    return evidence(artifact("change"), gate("build-ready"), *extra)


def test_latest_failure_and_alias_recovery() -> None:
    with fixture() as (workplace, project, started):
        first = transition(workplace, project, "brief", "prepare-ready")
        require(first.get("action") == "stage_transitioned", first)
        failed = call_mcp(
            workplace,
            "pf.work.transition",
            {
                "project_root": str(project),
                "outcome": "completed",
                "evidence": build_evidence(input_evidence("brief", "failed"), gate("prepare-ready", "failed")),
            },
        )
        incomplete_codes = {item.get("code") for item in failed.get("incomplete", []) if isinstance(item, dict)}
        require(failed.get("action") == "incomplete", failed)
        require({"required_input_missing", "gate_evidence_missing"}.issubset(incomplete_codes), failed)

        recovered = call_mcp(
            workplace,
            "pf.work.transition",
            {
                "project_root": str(project),
                "outcome": "completed",
                "evidence": build_evidence(input_evidence("brief"), gate("prepare-ready")),
            },
        )
        require(recovered.get("action") == "stage_transitioned" and recovered.get("next_stage_id") == "verify", recovered)

    with fixture() as (workplace, project, _started):
        require(transition(workplace, project, "brief", "prepare-ready").get("action") == "stage_transitioned", "prepare")
        failed = call_mcp(
            workplace,
            "pf.work.transition",
            {
                "project_root": str(project),
                "outcome": "completed",
                "evidence": build_evidence(input_evidence("brief", "failed")),
            },
        )
        require(failed.get("action") == "incomplete", failed)
        cross_kind = call_mcp(
            workplace,
            "pf.work.transition",
            {
                "project_root": str(project),
                "outcome": "completed",
                "evidence": build_evidence(artifact("brief"), input_evidence("unrelated", "failed")),
            },
        )
        require(cross_kind.get("action") == "stage_transitioned" and cross_kind.get("next_stage_id") == "verify", cross_kind)


def test_reentry_requires_current_outputs() -> None:
    with fixture() as (workplace, project, _started):
        require(transition(workplace, project, "brief", "prepare-ready").get("next_stage_id") == "build", "prepare")
        retry = transition(workplace, project, "change", "build-ready", outcome="retry")
        require(retry.get("action") == "stage_transitioned" and retry.get("next_stage_id") == "prepare", retry)
        reentered = state(workplace, project)
        codes = {item.get("code") for item in reentered.get("incomplete", []) if isinstance(item, dict)}
        require("artifact_evidence_missing" in codes, reentered)


def test_saved_file_changed_and_resubmitted() -> None:
    with fixture() as (workplace, project, _started):
        saved = project / "brief.md"
        saved.write_text("brief-v1", encoding="utf-8")
        first = call_mcp(
            workplace,
            "pf.work.transition",
            {
                "project_root": str(project),
                "outcome": "completed",
                "evidence": evidence(artifact("brief", path="brief.md"), gate("prepare-ready")),
            },
        )
        require(first.get("next_stage_id") == "build", first)
        saved.write_text("brief-v2", encoding="utf-8")
        stale = state(workplace, project)
        required_input = next(item for item in stale.get("required_inputs", []) if item.get("id") == "brief")
        require(required_input.get("satisfied") is False, stale)
        require(required_input.get("diagnostic", {}).get("code") == "evidence_file_changed", stale)
        blocked = transition(workplace, project, "change", "build-ready")
        require(blocked.get("action") == "incomplete", blocked)

        repaired = call_mcp(
            workplace,
            "pf.work.transition",
            {
                "project_root": str(project),
                "outcome": "completed",
                "evidence": build_evidence(input_evidence("brief", path="brief.md")),
            },
        )
        require(repaired.get("action") == "stage_transitioned" and repaired.get("next_stage_id") == "verify", repaired)

    with fixture() as (workplace, project, _started):
        saved = project / "brief.md"
        saved.write_text("brief", encoding="utf-8")
        first = call_mcp(
            workplace,
            "pf.work.transition",
            {
                "project_root": str(project),
                "outcome": "completed",
                "evidence": evidence(artifact("brief", path="brief.md"), gate("prepare-ready")),
            },
        )
        require(first.get("next_stage_id") == "build", first)
        saved.unlink()
        stale = state(workplace, project)
        required_input = next(item for item in stale.get("required_inputs", []) if item.get("id") == "brief")
        require(required_input.get("diagnostic", {}).get("code") == "evidence_file_missing", stale)
        blocked = transition(workplace, project, "change", "build-ready")
        require(blocked.get("action") == "incomplete", blocked)


def test_only_dependencies_are_freshness_checked() -> None:
    with fixture() as (workplace, project, _started):
        brief = project / "brief.md"
        obsolete = project / "obsolete.md"
        brief.write_text("brief", encoding="utf-8")
        obsolete.write_text("obsolete", encoding="utf-8")
        first = call_mcp(
            workplace,
            "pf.work.transition",
            {
                "project_root": str(project),
                "outcome": "completed",
                "evidence": evidence(artifact("brief", path="brief.md"), artifact("obsolete", path="obsolete.md"), gate("prepare-ready")),
            },
        )
        require(first.get("next_stage_id") == "build", first)
        obsolete.unlink()
        current = state(workplace, project)
        required_input = next(item for item in current.get("required_inputs", []) if item.get("id") == "brief")
        require(required_input.get("satisfied") is True, current)
        advanced = transition(workplace, project, "change", "build-ready")
        require(advanced.get("action") == "stage_transitioned", advanced)


def test_saved_gate_and_completion_freshness() -> None:
    with fixture() as (workplace, project, started):
        run_path = project / ".pf" / "runs" / str(started["run_id"]) / "run.yaml"
        run_data = yaml.safe_load(run_path.read_text(encoding="utf-8"))
        run_data["process_execution"]["definition"]["run_completion"] = {"gates": ["prepare-ready"]}
        run_data["process_execution"]["process_fingerprint"] = canonical_fingerprint(run_data["process_execution"]["definition"])
        run_path.write_text(yaml.safe_dump(run_data, allow_unicode=True, sort_keys=False), encoding="utf-8")
        gate_file = project / "prepare-gate.txt"
        gate_file.write_text("gate-v1", encoding="utf-8")
        first = call_mcp(
            workplace,
            "pf.work.transition",
            {
                "project_root": str(project),
                "outcome": "completed",
                "evidence": evidence(artifact("brief"), gate("prepare-ready", path="prepare-gate.txt")),
            },
        )
        require(first.get("next_stage_id") == "build", first)
        require(transition(workplace, project, "change", "build-ready").get("next_stage_id") == "verify", "build")
        gate_file.unlink()
        readiness = call_mcp(workplace, "pf.work.can_complete", {"project_root": str(project)})
        completion = next(item for item in readiness.get("blockers", []) if item.get("code") == "run_completion_gate_missing")
        require(completion.get("diagnostic", {}).get("code") == "evidence_file_missing", readiness)


def test_missing_digest_and_unsafe_path_are_explicit_and_read_only() -> None:
    with fixture() as (workplace, project, started):
        require(transition(workplace, project, "brief", "prepare-ready").get("next_stage_id") == "build", "prepare")
        assignment_path = project / ".pf" / "assignments" / f"{started['assignment_id']}.yaml"
        data = assignment(project, started)
        data["stage_history"][0]["evidence"].append({"kind": "artifact", "artifact_id": "brief", "status": "ready", "path": "brief.md"})
        assignment_path.write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8")
        before = assignment_path.read_bytes()
        missing_digest = state(workplace, project)
        after = assignment_path.read_bytes()
        required_input = next(item for item in missing_digest.get("required_inputs", []) if item.get("id") == "brief")
        require(required_input.get("diagnostic", {}).get("code") == "evidence_digest_missing", missing_digest)
        require(before == after, "state mutated stored evidence")

        data["stage_history"][0]["evidence"][-1] = {"kind": "artifact", "artifact_id": "brief", "status": "ready", "path": "../outside.md", "sha256": "sha256:0"}
        assignment_path.write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8")
        unsafe = state(workplace, project)
        required_input = next(item for item in unsafe.get("required_inputs", []) if item.get("id") == "brief")
        require(required_input.get("diagnostic", {}).get("code") == "evidence_file_unsafe", unsafe)


def test_normal_completion() -> None:
    with fixture() as (workplace, project, _started):
        require(transition(workplace, project, "brief", "prepare-ready").get("next_stage_id") == "build", "prepare")
        require(transition(workplace, project, "change", "build-ready").get("next_stage_id") == "verify", "build")
        finished = transition(workplace, project, "report", "verify-ready")
        require(finished.get("action") == "run_completed", finished)
        require(run(project, _started).get("status") == "completed", run(project, _started))


def main() -> int:
    test_latest_failure_and_alias_recovery()
    test_reentry_requires_current_outputs()
    test_saved_file_changed_and_resubmitted()
    test_only_dependencies_are_freshness_checked()
    test_saved_gate_and_completion_freshness()
    test_missing_digest_and_unsafe_path_are_explicit_and_read_only()
    test_normal_completion()
    print("PASS: Work evidence identity and file freshness")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
