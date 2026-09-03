#!/usr/bin/env python3
"""Deterministic Garage smoke coverage for multi-process Work Capsule isolation."""

from __future__ import annotations

import atexit
import shutil
import tempfile
from pathlib import Path
import sys

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from smoke_garage_mode_not_promoted_by_session import call_mcp, cli
from processforge_core.process_execution import project_process_selection


def write_process(project: Path, process_id: str, *, transitions: list[dict[str, str]] | None = None) -> None:
    process = {
        "schema_version": 1,
        "id": process_id,
        "name": process_id.replace("-", " ").title(),
        "version": "1.0.0",
        "status": "active",
        "description": f"Fixture process {process_id}.",
        "stages": [{"id": "work", "title": "Work", "required_role": "agent", "required_inputs": [], "produced_artifacts": [], "entry_gates": [], "exit_gates": []}],
        "artifact_definitions": [],
        "gates": [],
        "process_transitions": transitions or [],
        "stage_completion": {"handoff_note_required": True},
        "run_completion": {"summary_required": True, "handoff_artifact_required": True},
    }
    target = project / "processes" / "custom" / f"{process_id}.yaml"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(yaml.safe_dump(process, allow_unicode=True, sort_keys=False), encoding="utf-8")


def make_project(*, multi: bool, default: str = "") -> tuple[Path, Path]:
    root = Path(tempfile.mkdtemp(prefix="pf-multi-process-"))
    atexit.register(shutil.rmtree, root, ignore_errors=True)
    workplace, project = root / "workplace", root / "project"
    cli("workplace-init", "--workplace", str(workplace), "--apply")
    cli("project-onboard", "--project-root", str(project), "--workplace", str(workplace), "--type", "generic", "--apply")
    write_process(project, "architecture-analysis", transitions=[{"to_process": "software-feature-development"}])
    write_process(project, "software-feature-development")
    write_process(project, "testing")
    write_process(project, "not-allowed")
    manifest_path = project / ".pf" / "process-forge.yaml"
    manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    if multi:
        manifest.pop("process", None)
        manifest["processes"] = {"allowed": ["architecture-analysis", "software-feature-development", "testing"]}
        if default:
            manifest["processes"]["default"] = default
        cli("specialization-create", "--workplace", str(workplace), "--id", "fixture-architect", "--apply")
        manifest["specializations"] = {"allowed": ["fixture-architect"], "active": ["fixture-architect"]}
    else:
        manifest["process"] = "software-feature-development"
    manifest_path.write_text(yaml.safe_dump(manifest, allow_unicode=True, sort_keys=False), encoding="utf-8")
    cli("project-context-refresh", "--project-root", str(project), "--workplace", str(workplace), "--reason", "multi-process smoke fixture", "--apply")
    return workplace, project


def assert_case(name: str, condition: bool, payload: object) -> None:
    if not condition:
        raise AssertionError({"case": name, "payload": payload})
    print(f"PASS: {name}")


def main() -> int:
    workplace, legacy = make_project(multi=False)
    legacy_context = call_mcp(workplace, "pf.context", {"project_root": str(legacy)})
    legacy_start = call_mcp(workplace, "pf.work.start", {"project_root": str(legacy), "objective": "Legacy work"})
    assert_case("smoke_project_legacy_single_process_compatibility", legacy_context["process"]["default"] == "software-feature-development" and legacy_start["action"] == "created_new" and legacy_start["work_state"]["process"]["id"] == "software-feature-development", legacy_start)
    legacy_done = call_mcp(workplace, "pf.work.transition", {"project_root": str(legacy), "outcome": "completed", "notes": "legacy compatibility complete"})
    assert_case("smoke_legacy_single_process_completion", legacy_done["action"] == "run_completed", legacy_done)

    manifest_path = legacy / ".pf" / "process-forge.yaml"
    manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    manifest.pop("process", None)
    manifest["processes"] = {"default": "software-feature-development", "allowed": ["architecture-analysis", "software-feature-development", "testing"]}
    cli("specialization-create", "--workplace", str(workplace), "--id", "fixture-architect", "--apply")
    manifest["specializations"] = {"allowed": ["fixture-architect"], "active": ["fixture-architect"]}
    manifest_path.write_text(yaml.safe_dump(manifest, allow_unicode=True, sort_keys=False), encoding="utf-8")
    cli("project-context-refresh", "--project-root", str(legacy), "--workplace", str(workplace), "--reason", "multi process smoke fixture", "--apply")
    project = legacy
    context = call_mcp(workplace, "pf.context", {"project_root": str(project)})
    allowed = {item["id"] for item in context["process"]["allowed"]}
    assert_case("smoke_project_multiple_allowed_processes", allowed == {"architecture-analysis", "software-feature-development", "testing"} and "stages" not in str(context["process"]), context)
    choice = call_mcp(workplace, "pf.work.start", {"project_root": str(project), "objective": "Analyze idea"})
    assert_case("smoke_work_start_multiple_processes_requires_choice", choice["action"] == "process_choice_required" and choice["default_process"] == "software-feature-development" and {item["id"] for item in choice["candidates"]} == allowed and any(item["default"] for item in choice["candidates"]), choice)
    denied = call_mcp(workplace, "pf.work.start", {"project_root": str(project), "objective": "Forbidden", "process_id": "not-allowed"})
    assert_case("smoke_work_start_rejects_disallowed_process", denied["reason"] == "process_not_allowed", denied)
    started = call_mcp(workplace, "pf.work.start", {"project_root": str(project), "objective": "Analyze idea", "process_id": "architecture-analysis"})
    assignment_path = project / ".pf" / "assignments" / f"{started['assignment_id']}.yaml"
    capsule_path = project / ".pf" / "contexts" / "assignment-capsules" / f"{started['assignment_id']}.capsule.yaml"
    assignment = yaml.safe_load(assignment_path.read_text(encoding="utf-8"))
    capsule = yaml.safe_load(capsule_path.read_text(encoding="utf-8"))
    state = call_mcp(workplace, "pf.work.state", {"project_root": str(project)})
    assert_case("smoke_work_start_explicit_allowed_process", started["action"] == "created_new" and state["process"]["id"] == "architecture-analysis", started)
    assert_case("smoke_active_work_has_single_process", assignment["process"] == "architecture-analysis" and capsule["process_execution"]["process_id"] == "architecture-analysis", capsule)
    assert_case("smoke_work_capsule_does_not_union_allowed_processes", "definitions" not in capsule["process_execution"] and capsule["process_execution"]["definition"]["id"] == "architecture-analysis", capsule)
    assert_case("smoke_active_specializations_pinned_to_work", assignment["selected_specializations"] == ["fixture-architect"] and capsule["context"]["selected_specializations"] == ["fixture-architect"], capsule)
    completed = call_mcp(workplace, "pf.work.transition", {"project_root": str(project), "outcome": "completed", "notes": "architecture complete"})
    assert_case("smoke_process_transition_next_work_recommendation", completed["action"] == "run_completed" and completed["next"].get("recommended_process") == "software-feature-development" and completed["session_continuity"]["recommendation"] == "auto", completed)
    fresh_context = call_mcp(workplace, "pf.context", {"project_root": str(project)})
    assert_case("smoke_pf_context_exposes_fresh_session_continuation", fresh_context.get("work", {}).get("governed") is False and fresh_context.get("continuation", {}).get("previous_run_id") == started["run_id"] and fresh_context["continuation"]["next"].get("recommended_process") == "software-feature-development", fresh_context)
    followup = call_mcp(workplace, "pf.work.start", {"project_root": str(project), "objective": "Implement approved design", "process_id": "software-feature-development"})
    assert_case("smoke_existing_work_start_contract_compatible", followup["action"] == "created_new" and followup["run_id"] != started["run_id"] and followup["work_state"]["process"]["id"] == "software-feature-development", followup)
    assert_case("smoke_multi_process_garage_sessionless", followup["session"]["status"] == "absent", followup)
    assert_case("smoke_multi_process_does_not_require_runtime", context["mode"] == "garage", context)

    followup_done = call_mcp(workplace, "pf.work.transition", {"project_root": str(project), "outcome": "completed", "notes": "implementation complete"})
    after_followup = call_mcp(workplace, "pf.context", {"project_root": str(project)})
    assert_case("smoke_consumed_handoff_not_reoffered", followup_done["action"] == "run_completed" and after_followup.get("continuation", {}).get("previous_run_id") != started["run_id"], after_followup)

    manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    manifest["processes"] = {"allowed": ["testing"]}
    manifest_path.write_text(yaml.safe_dump(manifest, allow_unicode=True, sort_keys=False), encoding="utf-8")
    cli("project-context-refresh", "--project-root", str(project), "--workplace", str(workplace), "--reason", "single-process compatibility fixture", "--apply")
    single = call_mcp(workplace, "pf.work.start", {"project_root": str(project), "objective": "Single process work"})
    assert_case("smoke_work_start_single_process_auto_select", single["action"] == "created_new" and single["work_state"]["process"]["id"] == "testing", single)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
