"""Shared immutable assignment intent and versioned execution contracts.

Lifecycle services retain authority over their journals. This module describes and
checks worker permissions; it does not claim to provide an operating-system sandbox.
"""
from __future__ import annotations

import copy
import fnmatch
import hashlib
import json
import os
from pathlib import Path
import re
import stat
from typing import Any

import yaml

from ..common.request_scope import safe_load


CONTRACT_VERSION = 1
SOURCE_LIMITS = {"files": 128, "file_bytes": 1024 * 1024, "total_bytes": 8 * 1024 * 1024}
ANALYSIS_MODES = {"read_only", "planning_only", "analysis_only", "analysis", "assurance"}
EXECUTION_MODES = ANALYSIS_MODES | {"docs_only", "implementation", "release_delivery", "remediation"}


class ContextContractError(ValueError):
    def __init__(self, code: str, **details: Any):
        super().__init__(code)
        self.code, self.details = code, details


def fingerprint(value: Any) -> str:
    return "sha256:" + hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")).hexdigest()


def portable_path(value: Any, *, glob: bool = False) -> str:
    if not isinstance(value, str) or not value or len(value) > 1024:
        raise ContextContractError("path_scope_invalid")
    result = value.replace("\\", "/")
    if (result.startswith("/") or ":" in result or "\x00" in result or ".." in result.split("/")
            or (not glob and any(char in result for char in "*?["))):
        raise ContextContractError("private_path_forbidden")
    result = result.removeprefix("./")
    if not result or result == ".":
        raise ContextContractError("path_scope_invalid")
    return result


def _strings(value: Any, *, paths: bool = False, glob: bool = False) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list) or len(value) > 256 or any(not isinstance(x, str) or not x.strip() for x in value):
        raise ContextContractError("assignment_contract_invalid")
    return sorted(set(portable_path(x.strip(), glob=glob) if paths else x.strip() for x in value))


def _portable_values(value: Any, *, path_ref: bool = False, depth: int = 0) -> None:
    if depth > 12:
        raise ContextContractError("assignment_contract_invalid")
    if isinstance(value, dict):
        for key, item in value.items():
            if key in {"resolved_path", "absolute_path", "local_root"}:
                raise ContextContractError("private_path_forbidden")
            if path_ref and key in {"path", "relative_path"} and item != "" and item != ".":
                portable_path(item)
            _portable_values(item, path_ref=path_ref or key == "path_ref", depth=depth + 1)
    elif isinstance(value, list):
        for item in value:
            _portable_values(item, path_ref=path_ref, depth=depth + 1)
    elif isinstance(value, str) and re.match(r"^(?:[A-Za-z]:[/\\]|[/\\])", value):
        raise ContextContractError("private_path_forbidden")


def normalized_assignment_contract(project_root: Path, assignment: Path, metadata: dict[str, Any], core: Any) -> dict[str, Any]:
    """Single compatibility normalization used by both capsule constructors."""
    for key in ("workspace_access", "ownership", "non_overlap", "expected_report", "coordination_requirements", "subagent_policy"):
        if key in metadata and not isinstance(metadata[key], dict):
            raise ContextContractError("assignment_contract_invalid")
    for key in ("context_artifacts", "required_outputs"):
        if key in metadata and (not isinstance(metadata[key], list) or len(metadata[key]) > 256):
            raise ContextContractError("assignment_contract_invalid")
    if "execution_mode" in metadata and not isinstance(metadata["execution_mode"], (str, dict)):
        raise ContextContractError("assignment_contract_invalid")
    for item in metadata.get("context_artifacts", []):
        if not isinstance(item, (dict, str)) or isinstance(item, dict) and not item.get("path"):
            raise ContextContractError("assignment_contract_invalid")
        if isinstance(item, dict):
            for key in ("required", "mutable_by_worker"):
                if key in item and type(item[key]) is not bool:
                    raise ContextContractError("assignment_contract_invalid")
    policy = metadata.get("subagent_policy") or {}
    for key in ("allow", "allowed", "allow_subagents", "require_reports", "require_subagent_reports"):
        if key in policy and type(policy[key]) is not bool:
            raise ContextContractError("assignment_contract_invalid")
    if "max_subagents" in policy and (type(policy["max_subagents"]) is not int or policy["max_subagents"] < 0):
        raise ContextContractError("assignment_contract_invalid")
    if "allowed_roles" in policy:
        _strings(policy["allowed_roles"])
    if policy.get("reports_dir"):
        portable_path(policy["reports_dir"])
    if "writer" in (metadata.get("ownership") or {}) and type(metadata["ownership"]["writer"]) is not bool:
        raise ContextContractError("assignment_contract_invalid")
    snapshot_path, _ = core.project_context_snapshot_paths(project_root)
    assignment_rel = portable_path(core.rel(assignment, project_root))
    allowed = _strings(metadata.get("allowed_files"), paths=True, glob=True)
    allowed.extend(x for x in _strings(metadata.get("allowed_globs"), paths=True, glob=True) if x not in allowed)
    read = _strings(metadata.get("allowed_read_files"), paths=True, glob=True)
    forbidden = _strings(metadata.get("forbidden_files"), paths=True, glob=True)
    mode = core.normalize_execution_mode(metadata.get("execution_mode"))
    mode = {"kind": "read_only", "code_changes_allowed": False, "artifact_changes_allowed": True, "requires_review": True, **mode}
    if not isinstance(mode["kind"], str) or mode["kind"] not in EXECUTION_MODES:
        raise ContextContractError("execution_mode_invalid")
    for key in ("code_changes_allowed", "artifact_changes_allowed", "requires_review"):
        if type(mode[key]) is not bool:
            raise ContextContractError("assignment_contract_invalid")
    if mode["kind"] in ANALYSIS_MODES:
        mode["code_changes_allowed"] = False
    ownership = core.normalize_ownership(metadata, allowed)
    for key in ("owned_files", "owned_globs"):
        ownership[key] = _strings(ownership.get(key), paths=True, glob=True)
    actions = _strings(metadata.get("allowed_actions")) if "allowed_actions" in metadata else ["read"]
    if "allowed_actions" not in metadata:
        if allowed and mode["artifact_changes_allowed"]:
            actions.append("write_artifact")
        if allowed and mode["code_changes_allowed"]:
            actions.append("write_product")
    denies = _strings(metadata.get("forbidden_actions"))
    if not mode["code_changes_allowed"]:
        denies.append("write_product")
    if not mode["artifact_changes_allowed"]:
        denies.append("write_artifact")
    denies = sorted(set(denies))
    actions = sorted(set(actions) - set(denies))
    sources = sorted(set(_strings(metadata.get("required_sources"), paths=True) + _strings(metadata.get("input_artifacts"), paths=True)))
    artifacts = core.normalize_context_artifacts(metadata.get("context_artifacts"))
    raw_artifacts = metadata.get("context_artifacts") or []
    for i, item in enumerate(artifacts):
        item["path"] = portable_path(item["path"])
        # Preserve an operator-declared checksum omitted by field normalization.
        raw = raw_artifacts[i] if isinstance(raw_artifacts, list) and i < len(raw_artifacts) else None
        if isinstance(raw, dict) and raw.get("checksum"):
            item["checksum"] = str(raw["checksum"])
    outputs = core.normalize_required_outputs(metadata.get("required_outputs"))
    for output in outputs:
        if output.get("path"):
            output["path"] = portable_path(output["path"])
    expected = copy.deepcopy(metadata.get("expected_report") or {})
    if not isinstance(expected, dict):
        raise ContextContractError("assignment_contract_invalid")
    if expected.get("artifact"):
        expected["artifact"] = portable_path(expected["artifact"])
    access = core.normalize_workspace_access(metadata.get("workspace_access"))
    _portable_values(access)
    if core.workspace_access_public_path_issues(access):
        raise ContextContractError("private_path_forbidden")
    result = {
        "assignment": {"id": str(metadata.get("id") or assignment.stem), "run_id": str(metadata.get("run_id") or ""),
                       "path": assignment_rel, "status": metadata.get("status", "ready"),
                       "objective": metadata.get("objective", ""), "execution_mode": mode},
        "context": {"required_sources": list(dict.fromkeys([core.rel(snapshot_path, project_root), assignment_rel, *sources])), "context_artifacts": artifacts},
        "scope": {"allowed_files": allowed, "allowed_read_files": read, "forbidden_files": forbidden,
                  "allowed_actions": actions, "forbidden_actions": denies, "ownership": ownership,
                  "non_overlap": core.normalize_non_overlap(metadata.get("non_overlap"), allowed)},
        "outputs": {"required_outputs": outputs, "expected_report": expected},
        "workspace_access": access,
        "agent_model": core.normalize_agent_model(metadata.get("agent_model") or metadata.get("model") or ""),
        "agent_reasoning_effort": core.normalize_agent_reasoning_effort(metadata.get("agent_reasoning_effort") or metadata.get("reasoning_effort") or ""),
        "subagent_policy": core.normalize_subagent_policy(metadata.get("subagent_policy")),
    }
    _portable_values({key: result[key] for key in ("scope", "outputs", "subagent_policy")})
    return result


def assignment_intent(project_root: Path, assignment_path: Path, metadata: dict[str, Any], core: Any) -> dict[str, Any]:
    normalized = normalized_assignment_contract(project_root, assignment_path, metadata, core)
    scope = copy.deepcopy(normalized["scope"])
    scope["non_overlap"].pop("overlap_check", None)
    intent = {
        "objective": normalized["assignment"]["objective"], "execution_mode": normalized["assignment"]["execution_mode"],
        "scope": scope, "required_sources": sorted(set(_strings(metadata.get("required_sources"), paths=True) + _strings(metadata.get("input_artifacts"), paths=True))),
        "context_artifacts": normalized["context"]["context_artifacts"], "outputs": normalized["outputs"],
        "workspace_access": normalized["workspace_access"], "subagent_policy": normalized["subagent_policy"],
        "required_capabilities": _strings(metadata.get("required_capabilities")), "optional_capabilities": _strings(metadata.get("optional_capabilities")),
        "process": copy.deepcopy(metadata.get("process") or ""), "selected_specializations": _strings(metadata.get("selected_specializations")),
        "coordination_requirements": copy.deepcopy(metadata.get("coordination_requirements") or {}),
        "director_inbox_submit_required": bool(metadata.get("director_inbox_submit_required", False)),
        "parameters": copy.deepcopy(metadata.get("parameters") or {}),
        "allowed_tools": _strings(metadata.get("allowed_tools")), "allowed_templates": _strings(metadata.get("allowed_templates")),
        "selected_sources": _strings(metadata.get("selected_sources")),
        "obligations": {key: _strings(metadata.get(key)) for key in
                        ("required_artifacts", "required_reviews", "quality_checklist", "completion_criteria", "handoff_requirements", "required_specializations")},
    }
    intent["obligations"].update(goal=str(metadata.get("goal") or ""), role=str(metadata.get("role") or ""),
                                 dependencies=copy.deepcopy(metadata.get("dependencies") or {}))
    if not isinstance(intent["parameters"], dict):
        raise ContextContractError("assignment_contract_invalid")
    # These names are explicit execution preferences, never permission grants.
    for key in ("diagnostics", "agent_model", "agent_reasoning_effort", "model", "reasoning_effort", "provider"):
        intent["parameters"].pop(key, None)
    if "egress" in metadata:
        from ..egress.contracts import EgressError, security_intent
        try:
            security = {"egress": metadata["egress"], "allowed_read_files": intent["scope"]["allowed_read_files"]}
            if "egress_predecessor" in metadata:
                security["predecessor"] = metadata["egress_predecessor"]
            validated = security_intent(security)
        except EgressError as exc:
            raise ContextContractError(exc.code) from None
        intent["egress"] = validated["egress"]
        if "predecessor" in validated:
            intent["egress_predecessor"] = validated["predecessor"]
    elif "egress_predecessor" in metadata:
        raise ContextContractError("egress_contract_required")
    _portable_values(intent)
    return intent


def scope_allows(scope: dict[str, Any], path: str, action: str) -> bool:
    path = portable_path(path)
    if action in scope.get("forbidden_actions", []) or action not in scope.get("allowed_actions", []):
        return False
    if any(fnmatch.fnmatchcase(path, item) for item in scope.get("forbidden_files", [])):
        return False
    patterns = scope.get("allowed_read_files", []) if action == "read" else scope.get("allowed_files", [])
    if action == "write_artifact" and not path.startswith(".pf/artifacts/"):
        return False
    return any(fnmatch.fnmatchcase(path, item) for item in patterns)


def _source(project: Path, source: str) -> dict[str, Any]:
    relative = portable_path(source)
    root = project.resolve()
    lexical = root / relative
    def checked() -> Path:
        cursor = root
        for part in Path(relative).parts:
            cursor = cursor / part
            if cursor.is_symlink():
                raise ContextContractError("path_scope_escape", path=relative)
        target = lexical.resolve(strict=True)
        if not target.is_relative_to(root) or not target.is_file():
            raise ContextContractError("path_scope_escape", path=relative)
        return target
    try:
        target = checked()
        with target.open("rb") as stream:
            before = os.fstat(stream.fileno())
            if not stat.S_ISREG(before.st_mode) or before.st_size > SOURCE_LIMITS["file_bytes"]:
                raise ContextContractError("required_source_budget_exceeded", path=relative)
            current = checked().stat()
            if (current.st_dev, current.st_ino) != (before.st_dev, before.st_ino):
                raise ContextContractError("required_source_changed", path=relative)
            raw = stream.read(SOURCE_LIMITS["file_bytes"] + 1)
            after = os.fstat(stream.fileno())
            final = checked().stat()
        if len(raw) > SOURCE_LIMITS["file_bytes"]:
            raise ContextContractError("required_source_budget_exceeded", path=relative)
        signature = lambda value: (value.st_dev, value.st_ino, value.st_size, value.st_mtime_ns)
        if signature(before) != signature(after) or signature(after) != signature(final):
            raise ContextContractError("required_source_changed", path=relative)
        return {"path": relative, "status": "available", "size": len(raw), "checksum": "sha256:" + hashlib.sha256(raw).hexdigest()}
    except FileNotFoundError as exc:
        raise ContextContractError("required_source_missing", path=relative) from exc
    except (OSError, RuntimeError) as exc:
        raise ContextContractError("required_source_unavailable", path=relative) from exc


def _capture_sources(project: Path, assignment_path: Path, intent: dict[str, Any], core: Any) -> tuple[list[dict], list[dict]]:
    declared = {item: {"path": item, "required": True} for item in intent["required_sources"]}
    conflicts: set[str] = set()
    for item in intent["context_artifacts"]:
        if not item.get("mutable_by_worker"):
            previous = declared.get(item["path"], {})
            if previous.get("checksum") and item.get("checksum") and previous["checksum"] != item["checksum"]:
                conflicts.add(item["path"])
            declared[item["path"]] = {**previous, **item, "required": bool(previous.get("required") or item.get("required", True))}
            if previous.get("checksum"):
                declared[item["path"]]["checksum"] = previous["checksum"]
    if len(declared) > SOURCE_LIMITS["files"]:
        return [], [{"code": "required_source_budget_exceeded"}]
    lifecycle = {core.rel(assignment_path, project), core.rel(core.project_context_snapshot_paths(project)[0], project)}
    records, blockers, total = [], [], 0
    for path, spec in sorted(declared.items()):
        try:
            if path in conflicts:
                raise ContextContractError("required_source_conflict", path=path)
            if path in lifecycle:
                raise ContextContractError("mutable_lifecycle_source", path=path)
            record = _source(project, path)
            total += record["size"]
            if total > SOURCE_LIMITS["total_bytes"]:
                raise ContextContractError("required_source_budget_exceeded", path=path)
            if spec.get("checksum") and spec["checksum"] != record["checksum"]:
                raise ContextContractError("required_source_changed", path=path)
        except ContextContractError as exc:
            record = {"path": path, "status": "unavailable", "reason": exc.code}
            if spec.get("required", True):
                blockers.append({"code": exc.code, "path": path})
        records.append({**record, "required": spec.get("required", True)})
    return records, blockers


def _run_matches(run: dict[str, Any], metadata: dict[str, Any]) -> bool:
    def process_id(value: Any) -> str:
        return str(value.get("id") or "") if isinstance(value, dict) else str(value or "")
    members = [item for item in run.get("tasks", []) if isinstance(item, dict) and item.get("id") == metadata.get("id")]
    if not metadata.get("run_id") or run.get("id") != metadata["run_id"] or len(members) != 1:
        return False
    member = members[0]
    if member.get("assignment") and member["assignment"] != f".pf/assignments/{metadata.get('id')}.yaml":
        return False
    # Compatibility Runs are containers for independently declared task
    # processes. A governed Run with an execution pin still has one process.
    legacy_container = "process_execution" not in run and process_id(run.get("process")) in {
        "task-batch-execution", "multi-agent-task-orchestration",
    }
    return bool(process_id(metadata.get("process"))) and (legacy_container or process_id(run.get("process")) == process_id(metadata.get("process")))


def _assignment_run(project: Path, metadata: dict[str, Any], core: Any) -> dict[str, Any]:
    run_id = str(metadata.get("run_id") or "")
    if not re.fullmatch(r"[a-z0-9]+(?:-+[a-z0-9]+)*", run_id):
        return {}
    path = core.locate_flow_root(project) / "runs" / run_id / "run.yaml"
    if not path.is_file() or path.is_symlink() or path.stat().st_size > 2 * 1024 * 1024:
        return {}
    if not path.resolve().is_relative_to(core.locate_flow_root(project).resolve()):
        return {}
    value = core.load_yaml_document(path)
    return value if isinstance(value, dict) else {}


def process_pin_for_assignment(project: Path, metadata: dict[str, Any], snapshot: dict[str, Any], core: Any) -> dict[str, Any]:
    from ..process_execution import ProcessExecutionService

    run_id = str(metadata.get("run_id") or "")
    if run_id:
        run = _assignment_run(project, metadata, core)
        if not _run_matches(run, metadata):
            return {}
        if "process_execution" in run:
            run_pin = run["process_execution"]
            if (not isinstance(run_pin, dict) or not isinstance(run_pin.get("definition"), dict)
                    or run_pin.get("process_fingerprint") != fingerprint(run_pin["definition"])):
                return {}
            return copy.deepcopy(run_pin)
    reference = metadata.get("process")
    process_id = reference.get("id", "") if isinstance(reference, dict) else str(reference or "")
    if not process_id:
        return {}
    try:
        resolved = core.resolve_process_definition(project, process_id)
    except (OSError, ValueError, SystemExit):
        return {}
    selected = sorted({str(item["id"]) for item in snapshot.get("resolved", {}).get("knowledge_resources", []) if isinstance(item, dict) and item.get("id")})
    result = ProcessExecutionService(project, None, core)._process_pin(resolved.process, resolved.path,
        active_specializations=_strings(metadata.get("selected_specializations")), selected_resource_ids=selected, allowed_processes=[process_id])
    result["capture_origin"] = "legacy_run_new_context" if run_id else "standalone_assignment_new_context"
    return result


def build_context_fields(project: Path, assignment_path: Path, metadata: dict[str, Any], snapshot: dict[str, Any],
                         core: Any, *, workplace: Path | None = None, pin: dict[str, Any] | None = None,
                         run_record: dict[str, Any] | None = None) -> dict[str, Any]:
    from .resources import build_resource_bindings

    normalized = normalized_assignment_contract(project, assignment_path, metadata, core)
    intent = assignment_intent(project, assignment_path, metadata, core)
    run = run_record if run_record is not None else _assignment_run(project, metadata, core)
    valid_run = _run_matches(run, metadata)
    pin = copy.deepcopy(pin if pin is not None else process_pin_for_assignment(project, metadata, snapshot, core))
    definition = pin.get("definition") or {}
    snapshot_meta = snapshot.get("snapshot") or {}
    snapshot_id = pin.get("snapshot_id") or snapshot_meta.get("id") or "project-context"
    snapshot_checksum = pin.get("snapshot_checksum") or "sha256:" + core.sha256_file(core.project_context_snapshot_paths(project)[0])
    if pin and (snapshot_id != snapshot_meta.get("id") or snapshot_checksum != "sha256:" + core.sha256_file(core.project_context_snapshot_paths(project)[0])):
        raise ContextContractError("context_generation_changed", remediation="create_successor_work")
    selected = _strings(pin.get("selected_resource_ids")) if pin else []
    bindings = build_resource_bindings(project, workplace, core, selected)
    # Process-wide capabilities describe the complete lifecycle, not the
    # delegated assignment. Empty assignment requirements must stay empty.
    # The full process and its stage requirements remain in the process pin.
    required = intent["required_capabilities"]
    optional = sorted(set(intent["optional_capabilities"]) - set(required))
    providers = core.load_registry_capability_providers(project, core.resolve_project_workplace_manifest(project))
    required_records, optional_records = core.capability_records(required, optional, providers)
    sources, blockers = _capture_sources(project, assignment_path, intent, core)
    blockers.extend({"code": "source_scope_denied", "path": item["path"]} for item in sources
                    if item.get("required") and item.get("status") == "available" and not scope_allows(normalized["scope"], item["path"], "read"))
    blockers.extend({"code": "capability_missing", "capability": item["id"]} for item in required_records if item["status"] == "missing")
    for output in normalized["outputs"]["required_outputs"]:
        if output.get("required", True) and (not output.get("path") or not any(scope_allows(normalized["scope"], output["path"], action) for action in ("write_artifact", "write_product"))):
            blockers.append({"code": "output_scope_denied", "output_id": output["id"]})
    report = normalized["outputs"]["expected_report"].get("artifact")
    if report and not any(scope_allows(normalized["scope"], report, action) for action in ("write_artifact", "write_product")):
        blockers.append({"code": "output_scope_denied", "output_id": "expected-report"})
    # Resolve stable process/task parameters without consulting a changed catalog
    # or mixing the current stage into the immutable context.
    resolution = {"status": "resolved", "resolved_parameters": copy.deepcopy(snapshot.get("resolved_parameters") or {}),
                  "sources": copy.deepcopy((snapshot.get("parameter_resolution") or {}).get("sources") or []),
                  "provenance": {}, "conflicts": []}
    core.add_parameter_source(resolution, source_id="assignment-process:" + str(pin.get("process_id") or ""), layer="process", parameters=core.parameter_payload(definition))
    parameters = core.merge_parameter_maps(resolution["resolved_parameters"], intent["parameters"], "assignment")
    initial_stage = next((item for item in definition.get("stages", []) if item.get("id") == metadata.get("stage")), {})
    core.add_parameter_source(resolution, source_id="assignment-stage:" + str(metadata.get("stage") or ""), layer="stage", parameters=core.parameter_payload(initial_stage))
    core.add_parameter_source(resolution, source_id="assignment", layer="task", parameters=core.parameter_payload(metadata))
    identity = {"kind": "work" if valid_run else "assignment", "project_id": core.project_id(project),
                "run_id": str(metadata.get("run_id") or ""), "assignment_id": normalized["assignment"]["id"],
                "context_id": str(metadata.get("id") or assignment_path.stem) + "-capsule"}
    if not valid_run:
        blockers.append({"code": "work_identity_incomplete"})
    elif not pin:
        blockers.append({"code": "process_pin_unavailable"})
    contract = {
        "contract_version": 2 if "egress" in intent else CONTRACT_VERSION, "identity": identity,
        "assignment_intent": intent, "assignment_intent_checksum": fingerprint(intent),
        "snapshot": {"id": snapshot_id, "checksum": snapshot_checksum},
        "process": {"id": pin.get("process_id", ""), "version": pin.get("process_version", ""), "fingerprint": pin.get("process_fingerprint", "")},
        "resources": {"selected_ids": selected, "bindings_checksum": fingerprint(bindings)},
        "scope": copy.deepcopy(normalized["scope"]), "required_sources": sources, "outputs": copy.deepcopy(normalized["outputs"]),
        "capabilities": {"required": required_records, "optional": optional_records}, "workspace_access": copy.deepcopy(normalized["workspace_access"]),
        "parameters": parameters, "coordination": core.capsule_coordination_block(snapshot, metadata),
        "worker_may_rebuild_context": False, "source_limits": dict(SOURCE_LIMITS),
        "readiness": {"status": "blocked" if blockers else "ready", "blockers": blockers},
    }
    if "egress" in intent:
        contract["egress"] = copy.deepcopy(intent["egress"])
    _portable_values(contract)
    contract["contract_checksum"] = fingerprint(contract)
    normalized["context"].update(snapshot_id=snapshot_id, selected_resource_ids=selected)
    normalized["context"]["parameter_sources"] = [item["id"] for item in resolution["sources"]]
    return {**normalized, "execution_contract": contract, "resource_bindings": bindings,
            "process_execution": pin, "capabilities": contract["capabilities"],
            "resolved_parameters": resolution["resolved_parameters"],
            "parameter_resolution_summary": {key: resolution[key] for key in ("status", "sources", "conflicts")},
            "resolved_resources": copy.deepcopy(snapshot.get("resolved", {}).get("knowledge_resources", []))}


def validate_execution_contract(project: Path, assignment_path: Path, metadata: dict[str, Any], capsule: dict[str, Any],
                                core: Any, *, check_sources: bool = True, require_ready: bool = False) -> dict[str, Any]:
    contract = capsule.get("execution_contract")
    if not isinstance(contract, dict):
        return {"status": "legacy", "reason": "legacy_contract_incomplete", "remediation": "create_successor_work"}
    try:
        if type(contract.get("contract_version")) is not int or contract["contract_version"] not in (1, 2):
            raise ContextContractError("contract_version_unsupported")
        if contract["contract_version"] == 2:
            from ..egress.contracts import EgressError, require_v2
            try:
                require_v2(contract)
            except EgressError as exc:
                raise ContextContractError(exc.code) from None
        elif "egress" in contract or "egress" in (contract.get("assignment_intent") or {}):
            raise ContextContractError("egress_contract_required")
        assignment_pin = metadata.get("process_execution") or {}
        if assignment_pin.get("assignment_capsule_checksum"):
            pinned_path = core.locate_flow_root(project) / "contexts" / "assignment-capsules" / (str(metadata.get("id") or "") + ".capsule.yaml")
            if (assignment_pin.get("assignment_capsule") != core.rel(pinned_path, project)
                    or not pinned_path.resolve().is_relative_to(core.locate_flow_root(project).resolve())
                    or pinned_path.is_symlink() or not pinned_path.is_file() or pinned_path.stat().st_size > 2 * 1024 * 1024):
                raise ContextContractError("immutable_context_changed")
            raw = pinned_path.read_bytes()
            if len(raw) > 2 * 1024 * 1024 or "sha256:" + hashlib.sha256(raw).hexdigest() != assignment_pin["assignment_capsule_checksum"]:
                raise ContextContractError("immutable_context_changed")
            if safe_load(raw.decode("utf-8-sig")) != capsule:
                raise ContextContractError("immutable_context_changed")
        required = {"identity", "assignment_intent", "assignment_intent_checksum", "snapshot", "process", "resources", "scope", "outputs", "capabilities", "workspace_access", "parameters", "coordination", "source_limits", "readiness", "required_sources", "contract_checksum", "worker_may_rebuild_context"}
        if not required.issubset(contract) or contract["worker_may_rebuild_context"] is not False:
            raise ContextContractError("execution_contract_invalid")
        if fingerprint({k: v for k, v in contract.items() if k != "contract_checksum"}) != contract["contract_checksum"]:
            raise ContextContractError("immutable_context_changed")
        if fingerprint(contract["assignment_intent"]) != contract["assignment_intent_checksum"]:
            raise ContextContractError("execution_contract_invalid")
        current_intent = assignment_intent(project, assignment_path, metadata, core)
        if fingerprint(current_intent) != contract["assignment_intent_checksum"]:
            raise ContextContractError("assignment_contract_changed", remediation="create_successor_work")
        identity = contract["identity"]
        if identity.get("kind") not in {"work", "assignment"}:
            raise ContextContractError("execution_contract_invalid")
        if (identity["project_id"] != core.project_id(project) or identity["assignment_id"] != metadata.get("id")
                or identity["run_id"] != str(metadata.get("run_id") or "") or identity["context_id"] != capsule.get("capsule", {}).get("id")):
            raise ContextContractError("work_context_mismatch")
        if identity["kind"] == "work":
            run = _assignment_run(project, metadata, core)
            if not _run_matches(run, metadata):
                raise ContextContractError("work_identity_mismatch")
            run_pin = run.get("process_execution") or {}
            if run_pin and contract["process"] != {"id": run_pin.get("process_id"), "version": run_pin.get("process_version"), "fingerprint": run_pin.get("process_fingerprint")}:
                raise ContextContractError("work_context_mismatch")
        # Advisory overlap diagnostics are signed, but excluded from assignment
        # intent. Compare declarative scope using that same representation.
        contract_scope = copy.deepcopy(contract["scope"])
        contract_scope["non_overlap"].pop("overlap_check", None)
        if contract_scope != current_intent["scope"] or contract["outputs"] != current_intent["outputs"] or contract["workspace_access"] != current_intent["workspace_access"]:
            raise ContextContractError("execution_contract_invalid")
        if contract["resources"]["bindings_checksum"] != fingerprint(capsule.get("resource_bindings")):
            raise ContextContractError("immutable_context_changed")
        pin = capsule.get("process_execution") or {}
        if contract["resources"]["selected_ids"] != capsule.get("context", {}).get("selected_resource_ids", []):
            raise ContextContractError("work_context_mismatch")
        snapshot = capsule.get("context_snapshot") or {}
        if contract["snapshot"] != {"id": snapshot.get("id"), "checksum": snapshot.get("sha256")}:
            raise ContextContractError("work_context_mismatch")
        if pin:
            if contract["process"] != {"id": pin.get("process_id"), "version": pin.get("process_version"), "fingerprint": pin.get("process_fingerprint")}:
                raise ContextContractError("work_context_mismatch")
            if pin.get("process_fingerprint") != fingerprint(pin.get("definition")):
                raise ContextContractError("process_pin_invalid")
        if check_sources:
            total = 0
            if not isinstance(contract["required_sources"], list) or len(contract["required_sources"]) > SOURCE_LIMITS["files"]:
                raise ContextContractError("required_source_budget_exceeded")
            for record in contract["required_sources"]:
                if record.get("status") != "available":
                    if record.get("required", True):
                        raise ContextContractError(record.get("reason") or "required_source_unavailable", path=record.get("path"))
                    continue
                actual = _source(project, record["path"])
                total += actual["size"]
                if total > SOURCE_LIMITS["total_bytes"]:
                    raise ContextContractError("required_source_budget_exceeded")
                if actual["checksum"] != record["checksum"] or actual["size"] != record["size"]:
                    raise ContextContractError("required_source_changed", path=record["path"])
        if require_ready:
            if identity["kind"] != "work":
                raise ContextContractError("work_identity_incomplete", remediation="create_successor_work")
            if contract["readiness"].get("status") not in {"ready", "blocked"} or not isinstance(contract["readiness"].get("blockers"), list):
                raise ContextContractError("execution_contract_invalid")
            blockers = contract["readiness"].get("blockers") or []
            if blockers:
                raise ContextContractError(blockers[0]["code"], blockers=blockers)
            if contract["readiness"]["status"] != "ready":
                raise ContextContractError("execution_contract_not_ready")
            providers = core.load_registry_capability_providers(project, core.resolve_project_workplace_manifest(project))
            missing = [item["id"] for item in contract["capabilities"]["required"] if item["id"] not in providers]
            if missing:
                raise ContextContractError("capability_missing", capabilities=missing)
        return {"status": "valid", "contract_version": contract["contract_version"], "assignment_intent_checksum": contract["assignment_intent_checksum"], "readiness": contract["readiness"]}
    except ContextContractError as exc:
        return {"status": "blocked", "reason": exc.code, **exc.details}
    except (KeyError, TypeError, ValueError, AttributeError, OSError, RuntimeError, yaml.YAMLError, UnicodeError):
        return {"status": "blocked", "reason": "execution_contract_invalid"}


def stage_view(capsule: dict[str, Any], metadata: dict[str, Any]) -> dict[str, Any]:
    definition = capsule.get("process_execution", {}).get("definition", {})
    stage = next((item for item in definition.get("stages", []) if item.get("id") == metadata.get("stage")), {})
    return {"id": str(metadata.get("stage") or ""), "parameters": copy.deepcopy(stage.get("parameters") or {}),
            "required_capabilities": copy.deepcopy(stage.get("required_capabilities") or []),
            "required_inputs": copy.deepcopy(stage.get("required_inputs") or []), "produced_artifacts": copy.deepcopy(stage.get("produced_artifacts") or [])}
