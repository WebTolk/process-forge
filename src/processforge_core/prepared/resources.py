"""Authorize bounded workplace resources for one prepared Work input.

This module prepares private navigation metadata only. It does not copy
resource bodies into the prepared document or turn metadata-only declarations
into filesystem access.
"""
from __future__ import annotations

import copy
import hashlib
from pathlib import Path
import re
from typing import Any

import yaml

from ..project.snapshot import load_snapshot
from ..work.resource_material import (
    DEFAULT_LIMITS,
    MaterialBudget,
    MaterialError,
    capture_material,
    metadata_descriptor,
)
from ..work.resources import WorkResourceError, _root
from ..work.resource_declarations import ResourceDeclarationPolicy


MAX_SNAPSHOT_BYTES = 2 * 1024 * 1024
SNAPSHOT_ID_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}\Z")
RESOURCE_GROUPS = ("knowledge_resources", "templates", "tools", "mcp")
REVOKED_STATUSES = {"disabled", "denied", "missing", "revoked", "unavailable"}


class _PreparedResourceError(ValueError):
    """A stable resource-admission reason suitable for preparation blocking."""


def _fail(reason: str) -> None:
    raise _PreparedResourceError(reason)


def _sha256(raw: bytes) -> str:
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def _bounded_yaml(path: Path, flow_root: Path, reason: str) -> tuple[dict[str, Any], str]:
    try:
        resolved_flow = flow_root.resolve(strict=True)
        if path.is_symlink():
            _fail(reason)
        target = path.resolve(strict=True)
    except (OSError, RuntimeError, ValueError):
        _fail(reason)
    try:
        target.relative_to(resolved_flow)
    except ValueError:
        _fail(reason)
    if not target.is_file() or target.stat().st_size > MAX_SNAPSHOT_BYTES:
        _fail(reason)
    try:
        raw = target.read_bytes()
        if len(raw) > MAX_SNAPSHOT_BYTES:
            _fail(reason)
        value = yaml.safe_load(raw.decode("utf-8-sig"))
    except (OSError, UnicodeError, yaml.YAMLError):
        _fail(reason)
    if not isinstance(value, dict):
        _fail(reason)
    return value, _sha256(raw)


def _resolved_rows(snapshot: dict[str, Any], group: str) -> list[dict[str, Any]]:
    resolved = snapshot.get("resolved")
    if not isinstance(resolved, dict):
        return []
    rows = resolved.get(group)
    return [item for item in rows if isinstance(item, dict)] if isinstance(rows, list) else []


def _unique_match(rows: list[dict[str, Any]], requested: Any, core: Any, reason: str) -> dict[str, Any]:
    try:
        matches = [row for row in rows if core.workspace_ref_matches_resource(row, requested)]
    except (TypeError, ValueError, AttributeError):
        _fail("resource_scope_invalid")
    if len(matches) != 1:
        _fail(reason)
    return matches[0]


def _resource_bindings(capsule: dict[str, Any]) -> dict[str, dict[str, Any]]:
    bindings = capsule.get("resource_bindings")
    if not isinstance(bindings, dict) or type(bindings.get("schema_version")) is not int or bindings.get("schema_version") != 1:
        _fail("legacy_contract_incomplete")
    rows = bindings.get("resources")
    if not isinstance(rows, list) or any(not isinstance(item, dict) for item in rows):
        _fail("resource_binding_invalid")
    result: dict[str, dict[str, Any]] = {}
    for row in rows:
        identifier = row.get("id")
        if not isinstance(identifier, str) or not identifier or identifier in result:
            _fail("resource_binding_invalid")
        result[identifier] = row
    return result


def _current_resource(current_rows: dict[str, dict[str, Any]], identifier: str) -> dict[str, Any]:
    row = current_rows.get(identifier)
    if row is None:
        _fail("resource_access_revoked")
    if str(row.get("status") or "available").lower() in REVOKED_STATUSES:
        _fail("resource_access_revoked")
    return row


def _authorize_knowledge(project: Path, workplace: Path, requested: list[Any], capsule: dict[str, Any],
                         pinned_snapshot: dict[str, Any], current_snapshot: dict[str, Any],
                         snapshot_id: str, snapshot_checksum: str, selected_ids: list[str],
                         stage_subset: list[str], core: Any) -> list[dict[str, Any]]:
    capsule_rows = capsule.get("resolved_resources")
    pinned_rows = _resolved_rows(pinned_snapshot, "knowledge_resources")
    if not isinstance(capsule_rows, list) or any(not isinstance(item, dict) for item in capsule_rows):
        _fail("resource_binding_invalid")
    if capsule_rows != pinned_rows:
        _fail("snapshot_generation_changed")
    bindings = _resource_bindings(capsule)
    try:
        current_rows = ResourceDeclarationPolicy(error=lambda: WorkResourceError).grant_rows(current_snapshot)
    except WorkResourceError as exc:
        _fail(exc.code)
    ids = set(selected_ids)
    subset = set(stage_subset)
    unique_by_request: set[str] = set()
    grants: list[dict[str, Any]] = []
    budget = MaterialBudget()

    for request in requested:
        pinned = _unique_match(capsule_rows, request, core, "resource_not_in_snapshot")
        identifier = str(pinned.get("id") or pinned.get("resource_id") or "")
        if not identifier or identifier in unique_by_request:
            _fail("resource_scope_invalid")
        unique_by_request.add(identifier)
        if identifier not in ids:
            _fail("resource_not_selected")
        if identifier not in subset:
            _fail("resource_not_in_stage")
        binding = bindings.get(identifier)
        if binding is None or binding.get("status") != "available":
            _fail(str((binding or {}).get("reason") or "resource_material_unavailable"))

        row = _current_resource(current_rows, identifier)
        try:
            reference = ResourceDeclarationPolicy(error=lambda: WorkResourceError).portable_reference(row)
            descriptor = metadata_descriptor(row, reference)
            metadata_fp = _fingerprint(descriptor)
            if metadata_fp != binding.get("metadata_fingerprint"):
                _fail("resource_generation_changed")
            root, resolved_reference = _root(project, workplace, core, row)
            actual, _ = capture_material(row, root, resolved_reference, include_content=False, budget=budget)
        except WorkResourceError as exc:
            _fail(exc.code)
        except MaterialError as exc:
            _fail(exc.code)
        except (OSError, RuntimeError, SystemExit):
            _fail("resource_material_unavailable")

        if actual.get("metadata_fingerprint") != binding.get("metadata_fingerprint") or actual.get("generation") != binding.get("generation"):
            _fail("resource_generation_changed")
        if any(actual.get(key) != binding.get(key) for key in ("material_fingerprint", "material_kind", "manifest")):
            _fail("resource_material_changed")

        provenance = {
            "snapshot_id": snapshot_id,
            "snapshot_checksum": snapshot_checksum,
            "resource_id": identifier,
            "generation": actual["generation"],
            "metadata_fingerprint": actual["metadata_fingerprint"],
            "material_fingerprint": actual["material_fingerprint"],
        }
        material_kind = str(actual.get("material_kind") or "none")
        grant: dict[str, Any] = {
            "id": identifier,
            "path_ref": copy.deepcopy(resolved_reference),
            "metadata": descriptor,
            "material_kind": material_kind,
            "navigation": "verified_declared_material" if material_kind == "fulltext" else "metadata_only",
            "provenance": provenance,
            "manifest": copy.deepcopy(actual.get("manifest") or []),
            "resolution": ({"status": "resolved", "path": str(root.resolve())}
                           if material_kind == "fulltext" else {"status": "metadata_only"}),
        }
        grants.append(grant)
    return grants


def _fingerprint(value: Any) -> str:
    from ..work.resource_material import canonical_fingerprint

    return canonical_fingerprint(value)


def _authorize_registry_group(project: Path, requested: list[Any], pinned_snapshot: dict[str, Any],
                              current_snapshot: dict[str, Any], group: str, core: Any, workplace: Path) -> list[dict[str, Any]]:
    if not requested:
        return []
    pinned_rows = _resolved_rows(pinned_snapshot, group)
    current_rows = _resolved_rows(current_snapshot, group)
    manifest = core.resolve_project_workplace_manifest(project)
    grants: list[dict[str, Any]] = []
    seen: set[str] = set()
    for request in requested:
        pinned = _unique_match(pinned_rows, request, core, "resource_not_in_snapshot")
        current = _unique_match(current_rows, request, core, "resource_access_revoked")
        if str(current.get("status") or "available").lower() in REVOKED_STATUSES:
            _fail("resource_access_revoked")
        identifier = str(pinned.get("id") or pinned.get("resource_id") or pinned.get("name") or "")
        if not identifier or identifier in seen:
            _fail("resource_scope_invalid")
        seen.add(identifier)
        if current != pinned:
            _fail("resource_generation_changed")
        if isinstance(request, dict) and request.get("path_ref") and request.get("path_ref") != pinned.get("path_ref"):
            _fail("resource_reference_mismatch")
        path_ref = pinned.get("path_ref")
        if not isinstance(path_ref, dict) or not path_ref:
            _fail("resource_reference_unverifiable")
        try:
            resolution = core.resolve_workspace_path_ref(project, path_ref, workplace_manifest=manifest)
        except (OSError, ValueError, RuntimeError, SystemExit, AttributeError):
            _fail("resource_material_unavailable")
        if not isinstance(resolution, dict) or resolution.get("status") != "resolved" or not resolution.get("path"):
            _fail("resource_material_unavailable")
        grants.append({"id": identifier, "path_ref": copy.deepcopy(path_ref), "resolution": resolution})
    return grants


def authorize_resources(project: Path, task: dict[str, Any], capsule: dict[str, Any], core: Any) -> dict[str, Any]:
    """Return current-authorized workspace resources for a validated capsule.

    The caller validates the assignment execution contract first. All errors
    here are ``ValueError`` instances with stable machine-readable reasons.
    """
    try:
        project = Path(project).resolve(strict=True)
        if not isinstance(task, dict) or not isinstance(capsule, dict):
            _fail("prepared_input_invalid")
        task_id = str(task.get("id") or "")
        run_id = str(task.get("run_id") or "")
        if not task_id or not run_id:
            _fail("work_identity_incomplete")

        workplace = Path(core.resolve_workplace_root(None, project_root=project)).resolve(strict=True)
        check = core.project_context_check_result(project, explicit_workplace=str(workplace))
        if not isinstance(check, dict) or check.get("status") not in {"fresh", "fresh_with_updates"}:
            _fail("snapshot_not_fresh")

        contract = capsule.get("execution_contract")
        if not isinstance(contract, dict):
            _fail("legacy_contract_incomplete")
        identity = contract.get("identity")
        capsule_meta = capsule.get("capsule") if isinstance(capsule.get("capsule"), dict) else {}
        if (not isinstance(identity, dict) or identity.get("kind") != "work"
                or identity.get("project_id") != core.project_id(project)
                or identity.get("run_id") != run_id or identity.get("assignment_id") != task_id
                or identity.get("context_id") != capsule_meta.get("id")
                or capsule.get("assignment", {}).get("id") != task_id
                or capsule.get("assignment", {}).get("run_id") != run_id):
            _fail("work_identity_incomplete")
        contract_access = contract.get("workspace_access")
        if not isinstance(contract_access, dict):
            _fail("assignment_contract_invalid")
        requested = core.normalize_workspace_access(task.get("workspace_access"))
        if requested != contract_access:
            _fail("assignment_contract_changed")
        capsule_access = capsule.get("workspace_access")
        if isinstance(capsule_access, dict) and capsule_access != contract_access:
            _fail("immutable_context_changed")
        if core.workspace_access_public_path_issues(requested):
            _fail("private_path_forbidden")
        scope = contract.get("scope") or {}
        if any(requested.values()) and ("read" not in scope.get("allowed_actions", []) or "read" in scope.get("forbidden_actions", [])):
            _fail("scope_denied")
        if any(len(requested[group]) > DEFAULT_LIMITS["resources"] for group in RESOURCE_GROUPS):
            _fail("resource_material_budget_exceeded")

        from ..composition import build_prepared_resource_snapshot_reader

        pinned_snapshot, current_snapshot, snapshot_id, snapshot_checksum = build_prepared_resource_snapshot_reader(
            flow_root=lambda: core.locate_flow_root,
            snapshot_paths=lambda: core.project_context_snapshot_paths,
            bounded_yaml=lambda: _bounded_yaml,
            current_snapshot=lambda: lambda selected: load_snapshot(selected, core),
            context_checker=lambda: core.project_context_check_result,
            selector_pattern=lambda: SNAPSHOT_ID_RE,
            fail=lambda: _fail,
        ).load(project, capsule, contract, workplace)
        resources_contract = contract.get("resources")
        selected_ids = resources_contract.get("selected_ids") if isinstance(resources_contract, dict) else None
        capsule_selected = capsule.get("context", {}).get("selected_resource_ids") if isinstance(capsule.get("context"), dict) else None
        if (not isinstance(selected_ids, list) or len(selected_ids) > DEFAULT_LIMITS["resources"]
                or any(not isinstance(item, str) for item in selected_ids)
                or selected_ids != capsule_selected or len(selected_ids) != len(set(selected_ids))):
            _fail("resource_scope_invalid")

        pin = capsule.get("process_execution") if isinstance(capsule.get("process_execution"), dict) else {}
        definition = pin.get("definition") if isinstance(pin.get("definition"), dict) else {}
        stage_id = task.get("stage")
        stage_subset = list(selected_ids)
        if stage_id:
            stages = definition.get("stages") if isinstance(definition.get("stages"), list) else []
            stage = next((item for item in stages if isinstance(item, dict) and item.get("id") == stage_id), None)
            if stage is None:
                _fail("work_stage_invalid")
            subset = stage.get("resource_subset", selected_ids)
            if not isinstance(subset, list) or any(not isinstance(item, str) for item in subset):
                _fail("stage_resource_subset_invalid")
            stage_subset = subset
            if not set(stage_subset).issubset(selected_ids):
                _fail("stage_resource_subset_invalid")

        grants = {
            "knowledge_resources": _authorize_knowledge(
                project, workplace, requested["knowledge_resources"], capsule, pinned_snapshot, current_snapshot,
                snapshot_id, snapshot_checksum, selected_ids, stage_subset, core,
            ),
            "templates": _authorize_registry_group(project, requested["templates"], pinned_snapshot, current_snapshot, "templates", core, workplace),
            "tools": _authorize_registry_group(project, requested["tools"], pinned_snapshot, current_snapshot, "tools", core, workplace),
            "mcp": _authorize_registry_group(project, requested["mcp"], pinned_snapshot, current_snapshot, "mcp", core, workplace),
        }
        return {
            "schema_version": 1,
            "requested": copy.deepcopy(requested),
            "grants": grants,
            "policy": {
                "do_not_copy_private_paths_to_public_artifacts": True,
                "assignment_scope_remains_project_relative": True,
            },
            "visibility": "private_runtime",
            "run_id": run_id,
            "task_id": task_id,
        }
    except _PreparedResourceError:
        raise
    except ValueError:
        _fail("resource_material_unavailable")
    except (WorkResourceError, MaterialError) as exc:
        _fail(exc.code)
    except (OSError, RuntimeError, SystemExit, yaml.YAMLError, UnicodeError, TypeError, KeyError, AttributeError):
        _fail("resource_material_unavailable")


__all__ = ["authorize_resources"]
