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
from .resource_selection import PreparedResourceSelectionPolicy


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

        from ..composition import build_prepared_registry_resource_reader

        registry_reader = build_prepared_registry_resource_reader(
            selection=lambda: PreparedResourceSelectionPolicy(
                matcher=lambda: core.workspace_ref_matches_resource,
                fail=lambda: _fail, revoked_statuses=lambda: REVOKED_STATUSES,
            ),
            workplace_manifest=lambda: core.resolve_project_workplace_manifest,
            path_resolver=lambda: core.resolve_workspace_path_ref,
            revoked_statuses=lambda: REVOKED_STATUSES,
            fail=lambda: _fail,
        )
        from ..composition import build_prepared_knowledge_resource_reader

        knowledge_reader = build_prepared_knowledge_resource_reader(
            selection=lambda: PreparedResourceSelectionPolicy(
                matcher=lambda: core.workspace_ref_matches_resource,
                fail=lambda: _fail, revoked_statuses=lambda: REVOKED_STATUSES,
            ),
            declarations=lambda: ResourceDeclarationPolicy(error=lambda: WorkResourceError),
            metadata=lambda: metadata_descriptor,
            root_resolver=lambda: lambda project, workplace, row: _root(project, workplace, core, row),
            material_capture=lambda: capture_material, budget=lambda: MaterialBudget,
            work_error=lambda: WorkResourceError, material_error=lambda: MaterialError, fail=lambda: _fail,
        )
        grants = {
            "knowledge_resources": knowledge_reader.read(
                project, workplace, requested["knowledge_resources"], capsule, pinned_snapshot, current_snapshot,
                snapshot_id, snapshot_checksum, selected_ids, stage_subset,
            ),
            "templates": registry_reader.read(project, requested["templates"], pinned_snapshot, current_snapshot, "templates"),
            "tools": registry_reader.read(project, requested["tools"], pinned_snapshot, current_snapshot, "tools"),
            "mcp": registry_reader.read(project, requested["mcp"], pinned_snapshot, current_snapshot, "mcp"),
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
