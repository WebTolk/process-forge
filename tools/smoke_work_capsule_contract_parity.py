from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path
import shutil
import sys
import tempfile

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT / "src"))

import processforge as core
import process_execution_smoke_support as support
from processforge_core.process_execution import ProcessExecutionService, canonical_fingerprint
from processforge_core.work_context import (
    SOURCE_LIMITS,
    ContextContractError,
    _capture_sources,
    _run_matches,
    _source,
    assignment_intent,
    build_context_fields,
    fingerprint,
    normalized_assignment_contract,
    portable_path,
    scope_allows,
    stage_view,
    validate_execution_contract,
)


def check(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def check_reason(result: dict, expected: str, label: str) -> None:
    check(result.get("status") in {"blocked", "legacy"} and result.get("reason") == expected,
          f"{label}: expected {expected}, got {result}")


def write_yaml(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(value, allow_unicode=True, sort_keys=False), encoding="utf-8")


def register_run_member(project: Path, run_doc: dict, task: dict) -> dict:
    run_path = project / ".pf" / "runs" / str(run_doc["id"]) / "run.yaml"
    persisted = core.load_yaml_document(run_path)
    tasks = persisted.get("tasks") if isinstance(persisted.get("tasks"), list) else []
    if not any(isinstance(item, dict) and item.get("id") == task["id"] for item in tasks):
        tasks.append({"id": task["id"], "status": str(task.get("status") or "in_progress")})
        persisted["tasks"] = tasks
        write_yaml(run_path, persisted)
    run_doc.clear()
    run_doc.update(persisted)
    return persisted


def contract_fields(project: Path, workplace: Path, run_doc: dict, task_path: Path, task: dict,
                    *, pin: dict | None = None) -> dict:
    run_record = register_run_member(project, run_doc, task)
    snapshot_path, _ = core.project_context_snapshot_paths(project)
    snapshot = core.load_yaml_document(snapshot_path)
    return build_context_fields(project, task_path, task, snapshot, core, workplace=workplace,
                                pin=copy.deepcopy(pin if pin is not None else run_doc["process_execution"]),
                                run_record=run_record)


def capsule_for(fields: dict, task: dict, pin: dict) -> dict:
    contract = fields["execution_contract"]
    return {
        "capsule": {"id": contract["identity"]["context_id"]},
        "context_snapshot": {"id": contract["snapshot"]["id"], "sha256": contract["snapshot"]["checksum"]},
        "context": {"selected_resource_ids": contract["resources"]["selected_ids"]},
        "resource_bindings": fields["resource_bindings"],
        "process_execution": copy.deepcopy(pin),
        "execution_contract": copy.deepcopy(contract),
    }


def validate(project: Path, task_path: Path, task: dict, capsule: dict, *, require_ready: bool = False) -> dict:
    return validate_execution_contract(project, task_path, task, capsule, core, require_ready=require_ready)


def check_run_membership() -> None:
    task = {"id": "worker", "run_id": "container", "process": "worker-process"}
    for process in ("task-batch-execution", "multi-agent-task-orchestration"):
        run = {"id": "container", "process": process,
               "tasks": [{"id": "worker", "assignment": ".pf/assignments/worker.yaml"}]}
        check(_run_matches(run, task), f"native compatibility container rejected its worker: {process}")
        for invalid in (
            {**run, "process_execution": {}},
            {**run, "process": "unrelated-process"},
            {**run, "id": "other-run"},
            {**run, "tasks": []},
            {**run, "tasks": run["tasks"] * 2},
            {**run, "tasks": [{"id": "worker", "assignment": ".pf/assignments/other.yaml"}]},
        ):
            check(not _run_matches(invalid, task), f"invalid Run membership accepted: {invalid}")
        check(not _run_matches(run, {**task, "process": ""}), "empty worker process accepted")
        check(_run_matches({**run, "process": {"id": "worker-process"}, "process_execution": {}}, task),
              "same-process governed membership rejected")


def main() -> None:
    check_run_membership()
    checks: list[str] = ["compatibility containers preserve strict governed and unique Run membership"]
    skipped: list[str] = []
    original_process = copy.deepcopy(support.PROCESS)
    support.PROCESS["parameters"] = {"process_source": "original"}
    support.PROCESS["stages"][0]["parameters"] = {"stage_source": "prepare-original"}
    support.PROCESS["stages"][1]["parameters"] = {"stage_source": "build-original"}

    try:
        with tempfile.TemporaryDirectory(prefix="pf-work-contract-parity-") as scratch:
            scratch_root = Path(scratch)
            with support.fixture() as (workplace, project, started):
                run_doc = support.run(project, started)
                active_assignment = support.assignment(project, started)
                active_capsule_path = project / ".pf" / "contexts" / "assignment-capsules" / f"{started['assignment_id']}.capsule.yaml"
                active_capsule_bytes = active_capsule_path.read_bytes()
                active_capsule = yaml.safe_load(active_capsule_bytes)

                # The process and stage requirements remain lifecycle facts in the pin.
                active_contract = active_capsule["execution_contract"]
                check(active_contract["capabilities"]["required"] == [],
                      "process-wide/stage capabilities leaked into worker requirements")
                check(active_contract["readiness"]["status"] == "ready",
                      "lifecycle capability made an empty worker requirement unready")
                checks.append("process and stage capabilities remain lifecycle requirements")

                task = copy.deepcopy(active_assignment)
                task["id"] = "t03-contract-parity"
                task["objective"] = "Verify complete contract parity"
                task["required_sources"] = ["input.md"]
                task["required_capabilities"] = []
                task["optional_capabilities"] = []
                task["allowed_read_files"] = ["input.md"]
                task["allowed_files"] = [".pf/artifacts/t03-contract-parity.md"]
                task["allowed_actions"] = ["read", "write_artifact"]
                task["forbidden_actions"] = []
                task["required_outputs"] = [{"id": "report", "path": ".pf/artifacts/t03-contract-parity.md", "required": True}]
                task["execution_mode"] = {"kind": "read_only", "code_changes_allowed": False, "artifact_changes_allowed": True}
                task["process_execution"] = {key: value for key, value in task.get("process_execution", {}).items()
                                              if not key.startswith("assignment_capsule")}
                task_path = project / ".pf" / "assignments" / "t03-contract-parity.yaml"
                write_yaml(task_path, task)
                source_path = project / "input.md"
                source_path.write_text("pinned source bytes\n", encoding="utf-8")

                # Compare the actual governed and assignment capsule constructors in isolated copies.
                clone_governed = scratch_root / "governed-project"
                clone_assignment = scratch_root / "assignment-project"
                shutil.copytree(project, clone_governed)
                shutil.copytree(project, clone_assignment)
                governed_task_path = clone_governed / ".pf" / "assignments" / task_path.name
                assignment_task_path = clone_assignment / ".pf" / "assignments" / task_path.name
                governed_fields_task = copy.deepcopy(task)
                cli_fields_task = copy.deepcopy(task)
                write_yaml(governed_task_path, governed_fields_task)
                write_yaml(assignment_task_path, cli_fields_task)
                governed_run = register_run_member(clone_governed, support.run(clone_governed, started), governed_fields_task)
                register_run_member(clone_assignment, support.run(clone_assignment, started), cli_fields_task)
                governed_relative, governed_checksum = ProcessExecutionService(clone_governed, workplace, core)._write_capsule(
                    governed_run, governed_fields_task, copy.deepcopy(run_doc["process_execution"])
                )
                capsule_relative = f".pf/contexts/assignment-capsules/{task['id']}.capsule.yaml"
                governed_capsule_path = clone_governed / capsule_relative
                governed_capsule = yaml.safe_load(governed_capsule_path.read_text(encoding="utf-8"))
                governed_task_for_validation = copy.deepcopy(governed_fields_task)
                governed_task_for_validation["process_execution"]["assignment_capsule"] = governed_relative
                governed_task_for_validation["process_execution"]["assignment_capsule_checksum"] = governed_checksum
                write_yaml(governed_task_path, governed_task_for_validation)
                core.command_assignment_capsule(argparse.Namespace(
                    project_root=str(clone_assignment), assignment=str(assignment_task_path), force=False
                ))
                assignment_capsule_path = clone_assignment / capsule_relative
                assignment_capsule = yaml.safe_load(assignment_capsule_path.read_text(encoding="utf-8"))
                check(governed_capsule["execution_contract"] == assignment_capsule["execution_contract"],
                      "actual capsule constructors produced different execution contracts")
                checks.append("actual governed and assignment constructors have exact contract parity")

                lifecycle_pin = copy.deepcopy(run_doc["process_execution"])
                lifecycle_pin["definition"]["required_capabilities"] = ["process.lifecycle.only"]
                lifecycle_pin["definition"]["stages"][0]["required_capabilities"] = ["stage.lifecycle.only"]
                lifecycle_pin["process_fingerprint"] = canonical_fingerprint(lifecycle_pin["definition"])
                lifecycle_fields = contract_fields(clone_governed, workplace, governed_run, governed_task_path,
                                                   governed_fields_task, pin=lifecycle_pin)
                lifecycle_capsule = capsule_for(lifecycle_fields, governed_fields_task, lifecycle_pin)
                lifecycle_contract = lifecycle_fields["execution_contract"]
                check(lifecycle_contract["capabilities"]["required"] == [] and
                      lifecycle_contract["readiness"]["status"] == "ready",
                      "process-wide/stage capabilities became implicit worker requirements")
                check("process.lifecycle.only" in lifecycle_pin["definition"]["required_capabilities"],
                      "process requirement missing from pinned definition")
                stage_facts = stage_view(lifecycle_capsule, governed_fields_task)
                check("stage.lifecycle.only" in stage_facts["required_capabilities"],
                      "stage requirement missing from pinned stage view")
                check(lifecycle_contract["parameters"].get("process_source") == "original" and
                      stage_facts["parameters"] == {"stage_source": "prepare-original"},
                      "process or stage parameters were not read from the pin")
                checks.append("process/stage capability requirements stay in the pin, outside worker readiness")

                # The complete immutable contract validates; lifecycle/preferences are intentionally outside intent.
                check(validate(clone_governed, governed_task_path, governed_task_for_validation, governed_capsule, require_ready=True).get("status") == "valid",
                      "valid source/output assignment did not produce a ready contract")
                # A captured overlap diagnostic is signed data, not declarative scope.
                diagnostic_task = copy.deepcopy(task)
                diagnostic_task.setdefault("non_overlap", {})["overlap_check"] = {
                    "status": "fail", "conflicts": [{"other_assignment": "preceding-worker"}],
                }
                diagnostic_fields = contract_fields(clone_governed, workplace, governed_run,
                                                     governed_task_path, diagnostic_task)
                diagnostic_capsule = capsule_for(diagnostic_fields, diagnostic_task,
                                                  diagnostic_fields["process_execution"])
                check(validate(clone_governed, governed_task_path, diagnostic_task,
                               diagnostic_capsule, require_ready=True).get("status") == "valid",
                      "signed advisory overlap diagnostic invalidated the complete contract")
                diagnostic_bytes = copy.deepcopy(diagnostic_capsule)
                changed_diagnostic = copy.deepcopy(diagnostic_task)
                changed_diagnostic["non_overlap"]["overlap_check"] = {"status": "pass", "conflicts": []}
                check(validate(clone_governed, governed_task_path, changed_diagnostic,
                               diagnostic_capsule, require_ready=True).get("status") == "valid",
                      "current diagnostic was incorrectly treated as immutable intent")
                check(diagnostic_capsule == diagnostic_bytes, "scope validation mutated captured evidence")
                tampered_diagnostic = copy.deepcopy(diagnostic_capsule)
                tampered_diagnostic["execution_contract"]["scope"]["non_overlap"]["overlap_check"]["status"] = "pass"
                check_reason(validate(clone_governed, governed_task_path, diagnostic_task, tampered_diagnostic),
                             "immutable_context_changed", "signed overlap diagnostic mutation")
                broadened = copy.deepcopy(diagnostic_capsule)
                broadened_contract = broadened["execution_contract"]
                broadened_contract["scope"]["allowed_files"].append("src/**")
                broadened_contract["contract_checksum"] = fingerprint({
                    key: value for key, value in broadened_contract.items() if key != "contract_checksum"
                })
                check_reason(validate(clone_governed, governed_task_path, diagnostic_task, broadened),
                             "execution_contract_invalid", "broadened declarative scope with recomputed inner checksum")
                checks.append("signed overlap diagnostics remain advisory; scope grants and immutable bytes stay protected")

                forged = copy.deepcopy(governed_capsule)
                forged_source = forged["execution_contract"]["required_sources"][0]
                forged_source["checksum"] = "sha256:" + "f" * 64
                forged["execution_contract"]["contract_checksum"] = fingerprint({
                    key: value for key, value in forged["execution_contract"].items() if key != "contract_checksum"
                })
                check_reason(validate(clone_governed, governed_task_path, governed_task_for_validation, forged),
                             "immutable_context_changed", "forged inner source checksum under outer capsule pin")
                checks.append("recomputed inner checksum cannot bypass the governed capsule byte anchor")
                for key, value in {
                    "status": "review", "stage": "build", "stage_status": "completed",
                    "updated_at": "later", "stage_history": [{"some": "new evidence"}],
                    "result": {"status": "done", "summary": "lifecycle update"},
                    "session_id": "new-session", "retry": 4, "agent_model": "other-model",
                    "agent_reasoning_effort": "high", "diagnostics": {"profile": "trace"},
                }.items():
                    lifecycle = copy.deepcopy(task)
                    lifecycle[key] = value
                    lifecycle["parameters"] = {**lifecycle.get("parameters", {}), "model": "other", "reasoning_effort": "high",
                                                "provider": "other", "diagnostics": {"level": "debug"}}
                    lifecycle["process_execution"] = copy.deepcopy(governed_task_for_validation["process_execution"])
                    check(validate(clone_governed, governed_task_path, lifecycle, governed_capsule).get("status") == "valid",
                          f"lifecycle/preference field {key} changed immutable intent")
                checks.append("status, stage, evidence, timestamps, retry/session and preferences retain intent")

                for key, value in {
                    "objective": "changed objective",
                    "allowed_files": ["src/changed.py"],
                    "required_outputs": [{"id": "other", "path": ".pf/artifacts/other.md", "required": True}],
                    "required_capabilities": ["worker.capability.missing"],
                    "workspace_access": {"tools": ["tool.new"]},
                    "input_artifacts": ["another-input.md"],
                    "completion_criteria": ["different completion obligation"],
                }.items():
                    changed = copy.deepcopy(task)
                    changed[key] = value
                    changed["process_execution"] = copy.deepcopy(governed_task_for_validation["process_execution"])
                    check_reason(validate(clone_governed, governed_task_path, changed, governed_capsule),
                                 "assignment_contract_changed", f"intent mutation {key}")
                checks.append("objective, scope, output, capability and workspace mutations are rejected")

                # Empty allowlists and empty selected resources grant no authority.
                empty = copy.deepcopy(task)
                empty.update(allowed_files=[], allowed_read_files=[], allowed_actions=[], required_outputs=[])
                empty["ownership"] = {"owned_files": ["src/owned.py"], "owned_globs": ["src/**"]}
                empty_path = clone_governed / ".pf" / "assignments" / "t03-empty.yaml"
                write_yaml(empty_path, empty)
                empty_pin = copy.deepcopy(run_doc["process_execution"])
                empty_pin["selected_resource_ids"] = []
                empty_fields = contract_fields(clone_governed, workplace, run_doc, empty_path, empty, pin=empty_pin)
                empty_scope = empty_fields["execution_contract"]["scope"]
                check(empty_scope["allowed_files"] == [] and empty_scope["allowed_actions"] == [],
                      "ownership or defaults widened an empty allowlist")
                check(not scope_allows(empty_scope, "input.md", "read") and
                      not scope_allows(empty_scope, "src/owned.py", "write_product"),
                      "empty path/action scope granted access")
                check(empty_fields["execution_contract"]["resources"]["selected_ids"] == [] and
                      empty_fields["resource_bindings"]["resources"] == [],
                      "empty selected resources were widened")
                checks.append("empty path/action/resource grants remain empty")

                # Contradictory analysis-mode writes are denied.
                analysis = copy.deepcopy(task)
                analysis["execution_mode"] = {"kind": "analysis_only", "code_changes_allowed": True, "artifact_changes_allowed": True}
                analysis["allowed_files"] = ["src/product.py"]
                analysis["allowed_actions"] = ["read", "write_product"]
                analysis_path = clone_governed / ".pf" / "assignments" / "t03-analysis.yaml"
                write_yaml(analysis_path, analysis)
                analysis_scope = contract_fields(clone_governed, workplace, run_doc, analysis_path, analysis)["execution_contract"]["scope"]
                check("write_product" in analysis_scope["forbidden_actions"] and
                      not scope_allows(analysis_scope, "src/product.py", "write_product"),
                      "analysis mode allowed product writes")
                checks.append("analysis mode denies product writes despite contradictory defaults")

                for key, value, expected in (
                    ("execution_mode", {"kind": "mystery_mode"}, "execution_mode_invalid"),
                    ("subagent_policy", {"allow": "false"}, "assignment_contract_invalid"),
                ):
                    malformed = copy.deepcopy(task)
                    malformed[key] = value
                    try:
                        normalized_assignment_contract(clone_governed, governed_task_path, malformed, core)
                    except ContextContractError as exc:
                        check(exc.code == expected, f"{key} produced {exc.code}, expected {expected}")
                    else:
                        raise AssertionError(f"malformed {key} was silently normalized")
                bounded = copy.deepcopy(task)
                bounded["subagent_policy"] = {"allow": True, "max_subagents": 0}
                bounded_scope = normalized_assignment_contract(clone_governed, governed_task_path, bounded, core)
                check(bounded_scope["subagent_policy"]["max_subagents"] == 0,
                      "explicit zero subagent limit was replaced by a default")
                checks.append("invalid modes and malformed subagent policy fail closed; explicit zero limit remains zero")

                # Missing immutable material and explicit assignment capabilities are readiness blockers.
                missing_source = copy.deepcopy(task)
                missing_source["required_sources"] = ["does-not-exist.md"]
                missing_source_path = clone_governed / ".pf" / "assignments" / "t03-missing-source.yaml"
                write_yaml(missing_source_path, missing_source)
                missing_fields = contract_fields(clone_governed, workplace, run_doc, missing_source_path, missing_source)
                missing_codes = {item.get("code") for item in missing_fields["execution_contract"]["readiness"]["blockers"]}
                check("required_source_missing" in missing_codes, f"missing required source was not blocked: {missing_codes}")
                missing_cap = copy.deepcopy(task)
                missing_cap["required_capabilities"] = ["worker.capability.missing"]
                missing_cap_path = clone_governed / ".pf" / "assignments" / "t03-missing-cap.yaml"
                write_yaml(missing_cap_path, missing_cap)
                cap_fields = contract_fields(clone_governed, workplace, run_doc, missing_cap_path, missing_cap)
                check("capability_missing" in {item.get("code") for item in cap_fields["execution_contract"]["readiness"]["blockers"]},
                      "explicit missing worker capability was not blocked")
                check(cap_fields["execution_contract"]["capabilities"]["required"][0]["id"] == "worker.capability.missing",
                      "worker capability requirements do not match assignment declaration")
                checks.append("missing required source and explicit worker capability block readiness")

                # A missing or non-member run cannot turn an assignment into governed Work.
                nonmember = copy.deepcopy(task)
                nonmember["id"] = "t03-not-a-run-member"
                nonmember_path = clone_governed / ".pf" / "assignments" / "t03-not-a-run-member.yaml"
                write_yaml(nonmember_path, nonmember)
                snapshot_path, _ = core.project_context_snapshot_paths(clone_governed)
                nonmember_fields = build_context_fields(clone_governed, nonmember_path, nonmember,
                                                        core.load_yaml_document(snapshot_path), core,
                                                        workplace=workplace)
                nonmember_capsule = capsule_for(nonmember_fields, nonmember,
                                                nonmember_fields["process_execution"])
                check(nonmember_fields["execution_contract"]["identity"]["kind"] == "assignment" and
                      {item.get("code") for item in nonmember_fields["execution_contract"]["readiness"]["blockers"]} >= {"work_identity_incomplete"},
                      "non-member assignment was promoted to complete Work")
                check_reason(validate(clone_governed, nonmember_path, nonmember, nonmember_capsule, require_ready=True),
                             "work_identity_incomplete", "non-member run")
                fake_run = copy.deepcopy(task)
                fake_run.update(id="t03-missing-run", run_id="run-does-not-exist")
                fake_path = clone_governed / ".pf" / "assignments" / "t03-missing-run.yaml"
                write_yaml(fake_path, fake_run)
                fake_fields = build_context_fields(clone_governed, fake_path, fake_run,
                                                   core.load_yaml_document(snapshot_path), core,
                                                   workplace=workplace, run_record={})
                fake_capsule = capsule_for(fake_fields, fake_run, fake_fields["process_execution"])
                check(fake_fields["execution_contract"]["identity"]["kind"] == "assignment",
                      "missing run identity was labeled Work")
                check_reason(validate(clone_governed, fake_path, fake_run, fake_capsule, require_ready=True),
                             "work_identity_incomplete", "missing run")
                checks.append("missing/non-member runs remain incomplete assignment contexts")

                conflict = copy.deepcopy(task)
                conflict["context_artifacts"] = [
                    {"path": "input.md", "checksum": "sha256:" + "0" * 64, "required": True},
                    {"path": "input.md", "checksum": "sha256:" + "1" * 64, "required": True},
                ]
                conflict_path = clone_governed / ".pf" / "assignments" / "t03-source-conflict.yaml"
                write_yaml(conflict_path, conflict)
                conflict_fields = contract_fields(clone_governed, workplace, governed_run, conflict_path, conflict)
                check("required_source_conflict" in {item.get("code") for item in conflict_fields["execution_contract"]["readiness"]["blockers"]},
                      "conflicting immutable source declarations were not blocked")
                checks.append("conflicting immutable source checksums are rejected")

                # Portable path containment and symlink rejection.
                for forbidden in ("../outside.md", str(clone_governed.parent / "outside.md"), "C:/private/input.md"):
                    try:
                        portable_path(forbidden)
                    except ContextContractError:
                        pass
                    else:
                        raise AssertionError(f"unsafe source path accepted: {forbidden}")
                outside = clone_governed.parent / "outside.md"
                outside.write_text("outside", encoding="utf-8")
                link = clone_governed / "symlink-input.md"
                try:
                    link.symlink_to(outside)
                except (OSError, NotImplementedError) as exc:
                    skipped.append(f"symlink containment unavailable on host: {type(exc).__name__}")
                else:
                    try:
                        _source(clone_governed, "symlink-input.md")
                    except ContextContractError as exc:
                        check(exc.code == "path_scope_escape", f"unexpected symlink rejection: {exc.code}")
                    else:
                        raise AssertionError("symlink source escaped project root")
                checks.append("absolute/traversal and supported symlink source escapes are rejected")

                # Source-count, per-file and aggregate budgets are enforced.
                count_task = copy.deepcopy(task)
                count_task["required_sources"] = [f"missing-{index}.md" for index in range(SOURCE_LIMITS["files"] + 1)]
                count_intent = assignment_intent(clone_governed, governed_task_path, count_task, core)
                _, count_blockers = _capture_sources(clone_governed, governed_task_path, count_intent, core)
                check(count_blockers and count_blockers[0]["code"] == "required_source_budget_exceeded",
                      "source-count budget was not enforced")
                too_big = clone_governed / "too-big.md"
                too_big.write_bytes(b"x" * (SOURCE_LIMITS["file_bytes"] + 1))
                try:
                    _source(clone_governed, "too-big.md")
                except ContextContractError as exc:
                    check(exc.code == "required_source_budget_exceeded", "wrong per-file budget error")
                else:
                    raise AssertionError("per-file source budget was not enforced")
                aggregate_task = copy.deepcopy(task)
                aggregate_task["required_sources"] = []
                for index in range(SOURCE_LIMITS["total_bytes"] // SOURCE_LIMITS["file_bytes"] + 1):
                    name = f"aggregate-{index}.md"
                    (clone_governed / name).write_bytes(b"x" * SOURCE_LIMITS["file_bytes"])
                    aggregate_task["required_sources"].append(name)
                aggregate_intent = assignment_intent(clone_governed, governed_task_path, aggregate_task, core)
                _, aggregate_blockers = _capture_sources(clone_governed, governed_task_path, aggregate_intent, core)
                check(any(item.get("code") == "required_source_budget_exceeded" for item in aggregate_blockers),
                      "aggregate source budget was not enforced")
                checks.append("source-count, per-file and aggregate byte budgets are enforced")

                # Missing/changed source records and legacy/unknown contracts have distinct diagnoses.
                valid_fields = contract_fields(clone_governed, workplace, run_doc, governed_task_path, task)
                valid_capsule = capsule_for(valid_fields, task, run_doc["process_execution"])
                check(validate(clone_governed, governed_task_path, task, valid_capsule, require_ready=True).get("status") == "valid",
                      "valid generated contract failed its own source validation")
                (clone_governed / "input.md").write_text("changed source bytes\n", encoding="utf-8")
                check_reason(validate(clone_governed, governed_task_path, task, valid_capsule), "required_source_changed", "source byte mutation")
                (clone_governed / "input.md").unlink()
                check_reason(validate(clone_governed, governed_task_path, task, valid_capsule), "required_source_missing", "source deletion")
                (clone_governed / "input.md").write_text("pinned source bytes\n", encoding="utf-8")
                legacy = copy.deepcopy(valid_capsule)
                legacy.pop("execution_contract")
                check_reason(validate(clone_governed, governed_task_path, task, legacy), "legacy_contract_incomplete", "legacy capsule")
                unknown = copy.deepcopy(valid_capsule)
                unknown["execution_contract"]["contract_version"] = 999
                check_reason(validate(clone_governed, governed_task_path, task, unknown), "contract_version_unsupported", "unknown contract version")
                checks.append("missing/changed material, legacy absence and unknown contract version are diagnosed")

                # The assignment CLI's force option cannot replace its existing capsule.
                before_force = assignment_capsule_path.read_bytes()
                try:
                    core.command_assignment_capsule(argparse.Namespace(
                        project_root=str(clone_assignment), assignment=str(assignment_task_path), force=True
                    ))
                except SystemExit as exc:
                    check("immutable_context_exists" in str(exc), f"force returned an unexpected error: {exc}")
                else:
                    raise AssertionError("--force replaced an immutable contract capsule")
                check(assignment_capsule_path.read_bytes() == before_force, "--force changed existing capsule bytes")
                checks.append("--force refuses replacement without changing capsule bytes")

                # The real governed transition changes assignment lifecycle state, never the capsule bytes.
                before_transition = hashlib.sha256(active_capsule_path.read_bytes()).hexdigest()
                process_file = project / "processes" / "custom" / "declarative-smoke.yaml"
                live_process = yaml.safe_load(process_file.read_text(encoding="utf-8"))
                live_process["version"] = "9.9.9"
                live_process["parameters"] = {"process_source": "catalog-changed"}
                live_process["stages"][0]["parameters"] = {"stage_source": "catalog-stage-changed"}
                process_file.write_text(yaml.safe_dump(live_process, allow_unicode=True, sort_keys=False), encoding="utf-8")
                service = ProcessExecutionService(project, workplace, core)
                current_state = service.state()
                check(current_state["process"]["version"] == "1.0.0", "state followed changed process catalog instead of pin")
                pinned_stage = stage_view(active_capsule, active_assignment)
                check(pinned_stage["parameters"] == {"stage_source": "prepare-original"},
                      "stage view followed current catalog stage parameters")
                check(active_contract["parameters"].get("process_source") == "original",
                      "contract parameters were not captured from the pinned process")
                first = support.transition(workplace, project, "brief", "prepare-ready")
                check(first.get("action") == "stage_transitioned" and first.get("next_stage_id") == "build",
                      f"governed transition failed using process pin: {first}")
                after_transition = hashlib.sha256(active_capsule_path.read_bytes()).hexdigest()
                check(after_transition == before_transition, "governed transition rewrote capsule bytes")
                next_assignment = support.assignment(project, started)
                check(stage_view(active_capsule, next_assignment)["parameters"] == {"stage_source": "build-original"},
                      "current stage view did not come from the pinned process definition")
                checks.append("current catalog edits do not alter process/stage pins; governed transition preserves capsule bytes")

    finally:
        support.PROCESS.clear()
        support.PROCESS.update(original_process)

    print(json.dumps({"status": "PASS", "checks": checks, "skipped": skipped}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
