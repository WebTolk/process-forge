from __future__ import annotations

import json
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

import yaml

from smoke_garage_mode_not_promoted_by_session import call_mcp, cli


PROCESS = {
    "schema_version": 1,
    "id": "declarative-smoke",
    "name": "Declarative Smoke",
    "version": "1.0.0",
    "status": "active",
    "description": "Three-stage declarative execution fixture.",
    "initial_stage": "prepare",
    "roles": [{"id": "agent", "title": "Agent", "responsibility": "Execute fixture stages."}],
    "stages": [
        {
            "id": "prepare",
            "title": "Prepare",
            "required_role": "agent",
            "required_inputs": [],
            "produced_artifacts": ["brief"],
            "entry_gates": [],
            "exit_gates": ["prepare-ready"],
        },
        {
            "id": "build",
            "title": "Build",
            "required_role": "agent",
            "required_inputs": ["brief"],
            "produced_artifacts": ["change"],
            "entry_gates": ["prepare-ready"],
            "exit_gates": ["build-ready"],
            "outcomes": [
                {"id": "completed", "next_stage": "verify"},
                {"id": "retry", "next_stage": "prepare"},
            ],
        },
        {
            "id": "verify",
            "title": "Verify",
            "required_role": "agent",
            "required_inputs": ["change"],
            "produced_artifacts": ["report"],
            "entry_gates": ["build-ready"],
            "exit_gates": ["verify-ready"],
        },
    ],
    "artifact_definitions": [
        {"id": value, "title": value.title(), "owner_role": "agent", "lifecycle": ["draft", "approved"]}
        for value in ["brief", "change", "report"]
    ],
    "gates": [
        {"id": value, "description": value, "blocking": True, "required": True, "type": "checklist"}
        for value in ["prepare-ready", "build-ready", "verify-ready"]
    ],
    "evolution_policy": {},
    "process_transitions": [],
    "stage_completion": {"evidence_required": True},
    "run_completion": {"summary_required": True, "handoff_artifact_required": True},
}


@contextmanager
def fixture() -> Iterator[tuple[Path, Path, dict[str, Any]]]:
    with tempfile.TemporaryDirectory(prefix="pf-process-execution-") as raw:
        root = Path(raw)
        workplace = root / "workplace"
        project = root / "project"
        cli("workplace-init", "--workplace", str(workplace), "--apply")
        cli("project-onboard", "--project-root", str(project), "--workplace", str(workplace), "--type", "generic", "--apply")
        process_path = project / "processes" / "custom" / "declarative-smoke.yaml"
        process_path.parent.mkdir(parents=True, exist_ok=True)
        process_path.write_text(yaml.safe_dump(PROCESS, allow_unicode=True, sort_keys=False), encoding="utf-8")
        manifest_path = project / ".pf" / "process-forge.yaml"
        manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
        manifest["process"] = "declarative-smoke"
        manifest_path.write_text(yaml.safe_dump(manifest, allow_unicode=True, sort_keys=False), encoding="utf-8")
        cli("project-context-refresh", "--project-root", str(project), "--workplace", str(workplace), "--reason", "process execution smoke", "--apply")
        started = call_mcp(workplace, "pf.work.start", {"project_root": str(project), "objective": "Execute declarative smoke"})
        if started.get("action") != "created_new":
            raise AssertionError(started)
        yield workplace, project, started


def stage_evidence(artifact_id: str, gate_id: str) -> list[dict[str, str]]:
    return [
        {"kind": "artifact", "artifact_id": artifact_id, "status": "ready", "summary": f"{artifact_id} is ready"},
        {"kind": "gate", "gate_id": gate_id, "status": "passed", "summary": f"{gate_id} passed"},
    ]


def state(workplace: Path, project: Path) -> dict[str, Any]:
    return call_mcp(workplace, "pf.work.state", {"project_root": str(project)})


def transition(workplace: Path, project: Path, artifact_id: str, gate_id: str, outcome: str = "completed") -> dict[str, Any]:
    return call_mcp(
        workplace,
        "pf.work.transition",
        {
            "project_root": str(project),
            "outcome": outcome,
            "evidence": stage_evidence(artifact_id, gate_id),
            "notes": f"Complete {artifact_id}",
        },
    )


def assignment(project: Path, started: dict[str, Any]) -> dict[str, Any]:
    path = project / ".pf" / "assignments" / f"{started['assignment_id']}.yaml"
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def run(project: Path, started: dict[str, Any]) -> dict[str, Any]:
    path = project / ".pf" / "runs" / str(started["run_id"]) / "run.yaml"
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def event_types(project: Path) -> list[str]:
    path = project / ".pf" / "runtime" / "events" / "events.ndjson"
    return [str(json.loads(line).get("event_type")) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def scenario(name: str) -> None:
    with fixture() as (workplace, project, started):
        if name in {"initial_stage", "start_no_guessing"}:
            if started.get("stage") != "prepare" or started.get("stage_selection") != "process_initial_stage":
                raise AssertionError(started)
            capsule = project / ".pf" / "contexts" / "assignment-capsules" / f"{started['assignment_id']}.capsule.yaml"
            if not capsule.is_file():
                raise AssertionError("start did not create a pinned assignment capsule")
            capsule_data = yaml.safe_load(capsule.read_text(encoding="utf-8"))
            if not isinstance(capsule_data.get("context"), dict) or capsule_data["context"].get("snapshot_id") != capsule_data.get("context_snapshot", {}).get("id"):
                raise AssertionError("start did not create a schema-valid context capsule")
            return

        current = state(workplace, project)
        if name == "state_incomplete_not_blocked":
            if current.get("action") != "work_incomplete" or current.get("blockers") or "artifact_evidence_missing" not in {item.get("code") for item in current.get("incomplete", [])}:
                raise AssertionError(current)
            return
        if name == "blocked_state_is_distinct":
            path = project / ".pf" / "assignments" / f"{started['assignment_id']}.yaml"
            data = yaml.safe_load(path.read_text(encoding="utf-8"))
            data["stage_status"] = "blocked"
            data["stage_execution"]["blockers"] = [{"code": "operator_input_required"}]
            path.write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8")
            blocked = state(workplace, project)
            if blocked.get("action") != "work_blocked" or blocked.get("incomplete") is None or {item.get("code") for item in blocked.get("blockers", [])} != {"operator_input_required"}:
                raise AssertionError(blocked)
            return
        if name == "state_current_stage":
            required = {"process", "run", "assignment", "stage", "required_inputs", "obligations", "artifacts", "gates", "allowed_outcomes"}
            if current.get("stage", {}).get("id") != "prepare" or not required.issubset(current):
                raise AssertionError(current)
            return

        if name == "blocks_missing_gate":
            blocked = call_mcp(
                workplace,
                "pf.work.transition",
                {
                    "project_root": str(project),
                    "outcome": "completed",
                    "evidence": [{"kind": "artifact", "artifact_id": "brief", "status": "ready"}],
                },
            )
            if blocked.get("action") != "incomplete" or blocked.get("reason") != "stage_requirements_incomplete" or "gate_evidence_missing" not in {item.get("code") for item in blocked.get("incomplete", [])}:
                raise AssertionError(blocked)
            if assignment(project, started).get("stage_status") != "in_progress":
                raise AssertionError(assignment(project, started))
            return

        first = transition(workplace, project, "brief", "prepare-ready")
        if first.get("action") != "stage_transitioned" or first.get("next_stage_id") != "build":
            raise AssertionError(first)

        if name in {"linear", "updates_assignment_stage"}:
            if assignment(project, started).get("stage") != "build":
                raise AssertionError(assignment(project, started))
            return
        if name == "records_evidence":
            history = assignment(project, started).get("stage_history", [])
            if not history or {item.get("kind") for item in history[0].get("evidence", [])} != {"artifact", "gate"}:
                raise AssertionError(history)
            return
        if name == "emits_events":
            required_events = {"process.stage.started", "process.stage.completed", "process.stage.transitioned"}
            if not required_events.issubset(set(event_types(project))):
                raise AssertionError(event_types(project))
            return
        if name == "snapshot_pinned":
            before = run(project, started)["process_execution"]
            process_path = project / "processes" / "custom" / "declarative-smoke.yaml"
            changed = yaml.safe_load(process_path.read_text(encoding="utf-8"))
            changed["version"] = "9.9.9"
            changed["stages"][1]["id"] = "changed-live-stage"
            process_path.write_text(yaml.safe_dump(changed, allow_unicode=True, sort_keys=False), encoding="utf-8")
            pinned = state(workplace, project)
            if pinned.get("stage", {}).get("id") != "build" or pinned.get("process", {}).get("version") != "1.0.0":
                raise AssertionError(pinned)
            if run(project, started)["process_execution"]["process_fingerprint"] != before["process_fingerprint"]:
                raise AssertionError("pinned fingerprint changed")
            return
        if name == "branching":
            retry = transition(workplace, project, "change", "build-ready", outcome="retry")
            if retry.get("action") != "stage_transitioned" or retry.get("next_stage_id") != "prepare":
                raise AssertionError(retry)
            return

        second = transition(workplace, project, "change", "build-ready")
        if second.get("next_stage_id") != "verify":
            raise AssertionError(second)
        final = transition(workplace, project, "report", "verify-ready")
        if name == "final_completes_run":
            run_data = run(project, started)
            task_data = assignment(project, started)
            summary = project / ".pf" / "runs" / str(started["run_id"]) / "summary.md"
            handoff = project / ".pf" / "handoffs" / "runs" / f"{started['run_id']}-handoff.md"
            if final.get("action") != "run_completed" or run_data.get("status") != "completed" or task_data.get("status") != "done" or not summary.is_file() or not handoff.is_file():
                raise AssertionError({"final": final, "run": run_data, "assignment": task_data})
            return
        raise AssertionError(f"unknown scenario: {name}")
