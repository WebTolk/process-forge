"""Authorize bounded workplace resources for one prepared Work input.

This module prepares private navigation metadata only. It does not copy
resource bodies into the prepared document or turn metadata-only declarations
into filesystem access.
"""

from __future__ import annotations

import copy
import hashlib
import re
from pathlib import Path
from typing import Any, NoReturn

import yaml

from ..common.request_scope import safe_load as _safe_load_yaml
from ..project.snapshot import load_snapshot
from ..work.context_documents import ContextContractInputs
from ..work.resource_declarations import ResourceDeclarationPolicy
from ..work.resource_material import (
    DEFAULT_LIMITS,
    MaterialBudget,
    MaterialError,
    capture_material,
    metadata_descriptor,
)
from ..work.resources import WorkResourceError, _root
from .resource_selection import PreparedResourceSelectionPolicy

MAX_SNAPSHOT_BYTES = 2 * 1024 * 1024
SNAPSHOT_ID_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}\Z")
RESOURCE_GROUPS = ("knowledge_resources", "templates", "tools", "mcp")
REVOKED_STATUSES = {"disabled", "denied", "missing", "revoked", "unavailable"}


class _PreparedResourceError(ValueError):
    """A stable resource-admission reason suitable for preparation blocking."""


def _fail(reason: str) -> NoReturn:
    raise _PreparedResourceError(reason)


def _sha256(raw: bytes) -> str:
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def _bounded_yaml(
    path: Path, flow_root: Path, reason: str
) -> tuple[dict[str, Any], str]:
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
        value = _safe_load_yaml(raw.decode("utf-8-sig"))
    except (OSError, UnicodeError, yaml.YAMLError):
        _fail(reason)
    if not isinstance(value, dict):
        _fail(reason)
    return value, _sha256(raw)


def _native_authority(
    semantic: dict[str, Any], selected: dict[str, Any] | None = None
) -> dict[str, Any] | None:
    """Intersect the fixed private request, authoritative tool policy and Work.

    No file is read and no command is interpreted by this admission check.
    The standalone harness repeats this bounded check without importing Core.
    """
    import fnmatch
    import json

    def require(ok: bool, reason: str = "native_authority_required") -> None:
        if not ok:
            raise ValueError(reason)

    def seal(value: Any) -> str:
        return (
            "sha256:"
            + hashlib.sha256(
                (
                    json.dumps(
                        value,
                        sort_keys=True,
                        separators=(",", ":"),
                        ensure_ascii=True,
                        allow_nan=False,
                    )
                    + "\n"
                ).encode("ascii")
            ).hexdigest()
        )

    def pinned(value: Any) -> bool:
        return (
            isinstance(value, str)
            and re.fullmatch(r"sha256:[0-9a-f]{64}", value) is not None
        )

    def shape(value: Any) -> None:
        require(
            isinstance(value, dict)
            and set(value)
            == {
                "schema_version",
                "identity",
                "job_sha256",
                "descriptor_sha256",
                "runtime",
                "execute_sources",
                "operation",
                "management_sha256",
                "qualification_sha256",
                "deployment",
            }
        )
        require(type(value["schema_version"]) is int and value["schema_version"] == 1)
        ident = value["identity"]
        require(
            isinstance(ident, dict)
            and set(ident)
            == {
                "kind",
                "project_id",
                "run_id",
                "assignment_id",
                "context_id",
                "attempt",
            }
        )
        require(
            ident["kind"] == "work"
            and type(ident["attempt"]) is int
            and ident["attempt"] > 0
            and all(
                isinstance(ident[key], str)
                and re.fullmatch(r"[A-Za-z0-9_.-]{1,160}", ident[key]) is not None
                for key in set(ident) - {"kind", "attempt"}
            )
        )
        require(
            all(
                pinned(value[key])
                for key in (
                    "job_sha256",
                    "descriptor_sha256",
                    "management_sha256",
                    "qualification_sha256",
                )
            )
        )
        runtime = value["runtime"]
        require(
            isinstance(runtime, dict)
            and set(runtime) == {"resource_id", "access", "sha256", "version"}
        )
        require(
            runtime["resource_id"] == "management-python"
            and runtime["access"] == ["body", "execute"]
            and pinned(runtime["sha256"])
            and isinstance(runtime["version"], str)
            and 0 < len(runtime["version"]) <= 64
        )
        rows = value["execute_sources"]
        require(isinstance(rows, list) and len(rows) == 4)
        roles = set()
        for row in rows:
            require(
                isinstance(row, dict) and set(row) == {"role", "path", "sha256", "size"}
            )
            require(
                isinstance(row["role"], str)
                and row["role"] in {"wrapper", "harness", "controller", "native"}
                and row["role"] not in roles
                and isinstance(row["path"], str)
                and pinned(row["sha256"])
                and type(row["size"]) is int
                and 0 < row["size"] <= 32 * 1024 * 1024
            )
            roles.add(row["role"])
        operation = value["operation"]
        require(
            isinstance(operation, str)
            and operation
            in {
                "qualify-archive",
                "construct-management",
                "cold-stage",
                "cold-resume",
                "cold-finalize",
                "cold-release",
            }
        )
        deployment = value["deployment"]
        if operation in {"qualify-archive", "construct-management"}:
            require(deployment is None)
        else:
            require(
                isinstance(deployment, dict)
                and set(deployment)
                == {"access", "operations", "spec_sha256", "management_sha256"}
            )
            require(
                deployment["access"] == ["read", "write", "acl"]
                and deployment["operations"] == [operation]
                and pinned(deployment["spec_sha256"])
                and deployment["management_sha256"] == value["management_sha256"]
            )

    resources = semantic.get("resources", {})
    requests = resources.get("requested", {}).get("tools", [])
    grants = resources.get("grants", {}).get("tools", [])
    job = semantic.get("parameters", {}).get("native_maintenance_job")
    native_requests = [
        r for r in requests if isinstance(r, dict) and "native_maintenance" in r
    ]
    if job is None:
        require(not native_requests)
        return None
    require(
        isinstance(job, dict)
        and set(job)
        == {"schema_version", "identity", "operation", "resources", "runtime", "report"}
    )
    require(type(job["schema_version"]) is int and job["schema_version"] == 1)
    require(len(native_requests) == 1)
    request = native_requests[0]
    require(
        set(request) == {"id", "path_ref", "native_maintenance"}
        and isinstance(request["id"], str)
        and re.fullmatch(r"[A-Za-z0-9_.-]{1,160}", request["id"]) is not None
    )
    require(request["path_ref"] == {"registry": "tools", "id": request["id"]})
    require(
        sum(
            (
                r == request["id"]
                or isinstance(r, dict)
                and (
                    r.get("id") == request["id"]
                    or r.get("path_ref") == request["path_ref"]
                )
            )
            for r in requests
        )
        == 1
    )
    matches = [
        g
        for g in grants
        if isinstance(g, dict)
        and (g.get("id") == request["id"] or g.get("path_ref") == request["path_ref"])
    ]
    require(len(matches) == 1)
    grant = matches[0]
    require(
        set(grant) == {"id", "path_ref", "resolution"}
        and grant["id"] == request["id"]
        and grant["path_ref"] == request["path_ref"]
    )
    resolution = grant["resolution"]
    require(
        isinstance(resolution, dict)
        and set(resolution) == {"status", "entry"}
        and resolution["status"] == "descriptor"
    )
    entry = resolution["entry"]
    require(
        isinstance(entry, dict)
        and entry.get("id") == request["id"]
        and "path" not in entry
        and entry.get("status") == "configured"
        and entry.get("capability") == "processforge.native-maintenance.fixed-v1"
        and isinstance(entry.get("command"), str)
        and bool(entry["command"].strip())
    )
    policy = entry.get("native_maintenance")
    require(
        isinstance(policy, dict)
        and set(policy) == {"schema_version", "profile", "bindings"}
    )
    require(
        type(policy["schema_version"]) is int
        and policy["schema_version"] == 1
        and policy["profile"] == "native-maintenance-fixed-v1"
    )
    bindings = policy["bindings"]
    require(isinstance(bindings, list) and 0 < len(bindings) <= 64)
    for binding in bindings:
        shape(binding)
    require(len({seal(binding) for binding in bindings}) == len(bindings))
    binding = request["native_maintenance"]
    shape(binding)
    require(sum(binding == item for item in bindings) == 1)
    require(
        {key: value for key, value in binding["identity"].items() if key != "attempt"}
        == semantic.get("identity"),
        "native_identity_mismatch",
    )
    require(
        selected is None or selected == binding["identity"], "native_identity_mismatch"
    )
    require(
        job["identity"] == binding["identity"]
        and seal(job) == binding["job_sha256"]
        and job["runtime"] == binding["runtime"]
        and job["operation"] == binding["operation"],
        "native_job_mismatch",
    )
    scope = semantic.get("scope", {})

    def permitted(name: str, action: str, field: str) -> bool:
        return (
            action in scope.get("allowed_actions", [])
            and action not in scope.get("forbidden_actions", [])
            and name in scope.get(field, [])
            and not any(
                fnmatch.fnmatchcase(name.casefold(), pattern.casefold())
                for pattern in scope.get("forbidden_files", [])
            )
        )

    require("execute" not in scope.get("forbidden_actions", []), "native_scope_denied")
    require(
        isinstance(job["report"], str)
        and permitted(job["report"], "write_artifact", "allowed_files"),
        "native_scope_denied",
    )
    require(
        job["report"]
        == semantic.get("outputs", {}).get("expected_report", {}).get("artifact"),
        "native_report_mismatch",
    )
    rows = job["resources"]
    roles = {
        "wrapper",
        "harness",
        "controller",
        "native",
        "descriptor",
        "archive",
        "manifest",
        "management",
    }
    require(isinstance(rows, list) and len(rows) == len(roles))
    by_role = {}
    names = {job["report"].casefold()}
    for row in rows:
        require(
            isinstance(row, dict)
            and set(row) == {"role", "path", "access", "sha256", "size"}
        )
        name = row["path"]
        require(
            isinstance(name, str)
            and bool(name)
            and "\\" not in name
            and ":" not in name
            and "\x00" not in name
            and all(
                part not in {"", ".", ".."} and not part.endswith((".", " "))
                for part in name.split("/")
            )
        )
        require(
            isinstance(row["role"], str)
            and row["role"] in roles
            and row["role"] not in by_role
            and name.casefold() not in names
            and row["access"] == "body"
            and pinned(row["sha256"])
            and type(row["size"]) is int
            and 0 < row["size"] <= 128 * 1024 * 1024
        )
        require(permitted(name, "read", "allowed_read_files"), "native_scope_denied")
        sources = [
            s
            for s in semantic.get("sources", [])
            if isinstance(s, dict) and s.get("path") == name
        ]
        require(
            len(sources) == 1
            and sources[0].get("status") == "available"
            and sources[0].get("checksum") == row["sha256"]
            and sources[0].get("size") == row["size"],
            "native_source_body_required",
        )
        if selected is not None:
            require(
                sources[0].get("delivery") in {"inline", "reference"},
                "native_source_body_required",
            )
        by_role[row["role"]] = row
        names.add(name.casefold())
    require(
        by_role["descriptor"]["sha256"] == binding["descriptor_sha256"]
        and by_role["management"]["sha256"] == binding["management_sha256"],
        "native_source_pin_mismatch",
    )
    require(
        {row["role"]: row for row in binding["execute_sources"]}
        == {
            role: {
                key: value for key, value in by_role[role].items() if key != "access"
            }
            for role in ("wrapper", "harness", "controller", "native")
        },
        "native_execute_source_mismatch",
    )
    return binding


def authorize_resources(
    project: Path, task: dict[str, Any], capsule: dict[str, Any], core: Any
) -> dict[str, Any]:
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

        workplace = Path(
            core.resolve_workplace_root(None, project_root=project)
        ).resolve(strict=True)
        check = core.project_context_check_result(
            project, explicit_workplace=str(workplace)
        )
        if not isinstance(check, dict) or check.get("status") not in {
            "fresh",
            "fresh_with_updates",
        }:
            _fail("snapshot_not_fresh")

        contract = capsule.get("execution_contract")
        if not isinstance(contract, dict):
            _fail("legacy_contract_incomplete")
        identity = contract.get("identity")
        capsule_meta_value = capsule.get("capsule")
        capsule_meta = (
            capsule_meta_value if isinstance(capsule_meta_value, dict) else {}
        )
        if (
            not isinstance(identity, dict)
            or identity.get("kind") != "work"
            or identity.get("project_id") != core.project_id(project)
            or identity.get("run_id") != run_id
            or identity.get("assignment_id") != task_id
            or identity.get("context_id") != capsule_meta.get("id")
            or capsule.get("assignment", {}).get("id") != task_id
            or capsule.get("assignment", {}).get("run_id") != run_id
        ):
            _fail("work_identity_incomplete")
        contract_access = contract.get("workspace_access")
        if not isinstance(contract_access, dict):
            _fail("assignment_contract_invalid")
        requested = ContextContractInputs().normalize_workspace_access(
            task.get("workspace_access")
        )
        if requested != contract_access:
            _fail("assignment_contract_changed")
        capsule_access = capsule.get("workspace_access")
        if isinstance(capsule_access, dict) and capsule_access != contract_access:
            _fail("immutable_context_changed")
        if core.workspace_access_public_path_issues(requested):
            _fail("private_path_forbidden")
        scope = contract.get("scope") or {}
        if any(requested.values()) and (
            "read" not in scope.get("allowed_actions", [])
            or "read" in scope.get("forbidden_actions", [])
        ):
            _fail("scope_denied")
        if any(
            len(requested[group]) > DEFAULT_LIMITS["resources"]
            for group in RESOURCE_GROUPS
        ):
            _fail("resource_material_budget_exceeded")

        from ..composition import build_prepared_resource_snapshot_reader

        pinned_snapshot, current_snapshot, snapshot_id, snapshot_checksum = (
            build_prepared_resource_snapshot_reader(
                flow_root=lambda: core.locate_flow_root,
                snapshot_paths=lambda: core.project_context_snapshot_paths,
                bounded_yaml=lambda: _bounded_yaml,
                current_snapshot=lambda: lambda selected: load_snapshot(selected),
                context_checker=lambda: core.project_context_check_result,
                selector_pattern=lambda: SNAPSHOT_ID_RE,
                fail=lambda: _fail,
            ).load(project, capsule, contract, workplace)
        )
        resources_contract = contract.get("resources")
        selected_ids = (
            resources_contract.get("selected_ids")
            if isinstance(resources_contract, dict)
            else None
        )
        capsule_selected = (
            capsule.get("context", {}).get("selected_resource_ids")
            if isinstance(capsule.get("context"), dict)
            else None
        )
        if (
            not isinstance(selected_ids, list)
            or len(selected_ids) > DEFAULT_LIMITS["resources"]
            or any(not isinstance(item, str) for item in selected_ids)
            or selected_ids != capsule_selected
            or len(selected_ids) != len(set(selected_ids))
        ):
            _fail("resource_scope_invalid")

        pin_value = capsule.get("process_execution")
        pin = pin_value if isinstance(pin_value, dict) else {}
        definition_value = pin.get("definition")
        definition = definition_value if isinstance(definition_value, dict) else {}
        stage_id = task.get("stage")
        stage_subset = list(selected_ids)
        if stage_id:
            stages_value = definition.get("stages")
            stages = stages_value if isinstance(stages_value, list) else []
            stage = next(
                (
                    item
                    for item in stages
                    if isinstance(item, dict) and item.get("id") == stage_id
                ),
                None,
            )
            if stage is None:
                _fail("work_stage_invalid")
            subset = stage.get("resource_subset", selected_ids)
            if not isinstance(subset, list) or any(
                not isinstance(item, str) for item in subset
            ):
                _fail("stage_resource_subset_invalid")
            stage_subset = subset
            if not set(stage_subset).issubset(selected_ids):
                _fail("stage_resource_subset_invalid")

        from processforge_core.project.coordination_state import (
            ProjectCoordinationStateService,
        )
        from processforge_core.work.workspace_refs import (
            WorkspaceAccessReferenceService,
        )

        from ..composition import build_prepared_registry_resource_reader

        registry_reader = build_prepared_registry_resource_reader(
            selection=lambda: PreparedResourceSelectionPolicy(
                matcher=lambda: (
                    WorkspaceAccessReferenceService().workspace_ref_matches_resource
                ),
                fail=lambda: _fail,
                revoked_statuses=lambda: REVOKED_STATUSES,
            ),
            workplace_manifest=lambda: (
                ProjectCoordinationStateService().resolve_project_workplace_manifest
            ),
            path_resolver=lambda: core.resolve_workspace_path_ref,
            revoked_statuses=lambda: REVOKED_STATUSES,
            fail=lambda: _fail,
        )
        from ..composition import build_prepared_knowledge_resource_reader

        knowledge_reader = build_prepared_knowledge_resource_reader(
            selection=lambda: PreparedResourceSelectionPolicy(
                matcher=lambda: (
                    WorkspaceAccessReferenceService().workspace_ref_matches_resource
                ),
                fail=lambda: _fail,
                revoked_statuses=lambda: REVOKED_STATUSES,
            ),
            declarations=lambda: ResourceDeclarationPolicy(
                error=lambda: WorkResourceError
            ),
            metadata=lambda: metadata_descriptor,
            root_resolver=lambda: (
                lambda project, workplace, row: _root(project, workplace, row)
            ),
            material_capture=lambda: capture_material,
            budget=lambda: MaterialBudget,
            work_error=lambda: WorkResourceError,
            material_error=lambda: MaterialError,
            fail=lambda: _fail,
        )
        grants = {
            "knowledge_resources": knowledge_reader.read(
                project,
                workplace,
                requested["knowledge_resources"],
                capsule,
                pinned_snapshot,
                current_snapshot,
                snapshot_id,
                snapshot_checksum,
                selected_ids,
                stage_subset,
            ),
            "templates": registry_reader.read(
                project,
                requested["templates"],
                pinned_snapshot,
                current_snapshot,
                "templates",
            ),
            "tools": registry_reader.read(
                project, requested["tools"], pinned_snapshot, current_snapshot, "tools"
            ),
            "mcp": registry_reader.read(
                project, requested["mcp"], pinned_snapshot, current_snapshot, "mcp"
            ),
        }
        _native_authority(
            {
                "identity": identity,
                "parameters": contract.get("parameters", {}),
                "scope": scope,
                "sources": contract.get("required_sources", []),
                "outputs": contract.get("outputs", {}),
                "resources": {"requested": requested, "grants": grants},
            }
        )
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
    except ValueError as exc:
        if str(exc).startswith("native_"):
            _fail(str(exc))
        _fail("resource_material_unavailable")
    except (WorkResourceError, MaterialError) as exc:
        _fail(exc.code)
    except (
        OSError,
        RuntimeError,
        SystemExit,
        yaml.YAMLError,
        UnicodeError,
        TypeError,
        KeyError,
        AttributeError,
    ):
        _fail("resource_material_unavailable")


__all__ = ["authorize_resources"]
