#!/usr/bin/env python3
from __future__ import annotations

import copy
import json

import yaml

from process_execution_smoke_support import assignment, call_mcp, cli, fixture, run, stage_evidence, transition


def corrupt_pin_is_rejected() -> None:
    with fixture() as (workplace, project, started):
        path = project / ".pf" / "runs" / started["run_id"] / "run.yaml"
        original = yaml.safe_load(path.read_text(encoding="utf-8"))
        task = project / ".pf" / "assignments" / f"{started['assignment_id']}.yaml"
        capsule = project / ".pf" / "contexts" / "assignment-capsules" / f"{started['assignment_id']}.capsule.yaml"
        for corruption, expected in [("fingerprint", "work_context_mismatch"), ("definition", "process_pin_invalid")]:
            data = copy.deepcopy(original)
            if corruption == "fingerprint":
                # The complete contract rejects a run/capsule mismatch first.
                data["process_execution"]["process_fingerprint"] = "sha256:" + "0" * 64
            else:
                data["process_execution"]["definition"]["name"] = "Tampered definition"
            path.write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8")
            before = {item: item.read_bytes() for item in (path, task, capsule)}
            result = call_mcp(
                workplace,
                "pf.work.transition",
                {"project_root": str(project), "outcome": "completed", "evidence": stage_evidence("brief", "prepare-ready"), "notes": "Attempt corrupt pin"},
            )
            if result.get("action") != "blocked" or result.get("reason") != expected:
                raise AssertionError(result)
            if any(item.read_bytes() != content for item, content in before.items()):
                raise AssertionError("rejected corruption changed Work state")


def attestation_does_not_replace_artifact() -> None:
    with fixture() as (workplace, project, _started):
        result = call_mcp(
            workplace,
            "pf.work.transition",
            {
                "project_root": str(project),
                "outcome": "completed",
                "evidence": [
                    {"kind": "attestation", "id": "brief", "status": "ready", "summary": "Claim only"},
                    {"kind": "gate", "gate_id": "prepare-ready", "status": "passed"},
                ],
                "notes": "Attestation must not satisfy artifact",
            },
        )
        if result.get("action") != "incomplete" or "artifact_evidence_missing" not in {item.get("code") for item in result.get("incomplete", [])}:
            raise AssertionError(result)


def final_blocker_preserves_state() -> None:
    with fixture() as (workplace, project, started):
        transition(workplace, project, "brief", "prepare-ready")
        transition(workplace, project, "change", "build-ready")
        path = project / ".pf" / "runs" / started["run_id"] / "run.yaml"
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        data["tasks"].append({"id": "sibling-task", "assignment": ".pf/assignments/sibling-task.yaml", "status": "in_progress", "order": 2, "blocking": True})
        path.write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8")
        result = call_mcp(
            workplace,
            "pf.work.transition",
            {"project_root": str(project), "outcome": "completed", "evidence": stage_evidence("report", "verify-ready"), "notes": "Final attempt"},
        )
        task = assignment(project, started)
        if result.get("action") != "incomplete" or "blocking_assignment_incomplete" not in {item.get("code") for item in result.get("incomplete", [])}:
            raise AssertionError(result)
        if len(task.get("stage_history", [])) != 2 or not task.get("stage_execution", {}).get("evidence"):
            raise AssertionError(task)


def completed_run_is_immutable() -> None:
    with fixture() as (workplace, project, started):
        transition(workplace, project, "brief", "prepare-ready")
        transition(workplace, project, "change", "build-ready")
        transition(workplace, project, "report", "verify-ready")
        before = len(assignment(project, started).get("stage_history", []))
        evidence = json.dumps(stage_evidence("report", "verify-ready")[0])
        try:
            cli(
                "work-transition",
                "--project-root", str(project),
                "--workplace", str(workplace),
                "--run", started["run_id"],
                "--assignment", started["assignment_id"],
                "--outcome", "completed",
                "--evidence", evidence,
                "--notes", "Repeat completion",
                "--json",
            )
            raise AssertionError("terminal transition unexpectedly succeeded")
        except AssertionError as exc:
            payload = json.loads(str(exc))
        if payload.get("reason") != "work_is_terminal" or len(assignment(project, started).get("stage_history", [])) != before:
            raise AssertionError(payload)
        if run(project, started).get("status") != "completed":
            raise AssertionError(run(project, started))


def main() -> int:
    corrupt_pin_is_rejected()
    attestation_does_not_replace_artifact()
    final_blocker_preserves_state()
    completed_run_is_immutable()
    print("PASS: process execution integrity guards")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
