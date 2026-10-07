"""Shared application service for deterministic PF project initialization.

The Core owns request normalization, state classification and the explicit
write acknowledgement. The distribution CLI supplies existing writer and
doctor adapters, so CLI and controlled MCP follow one workflow.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from ..agent_entry.contract import EntryError
from ..agent_entry import migration as entry_migration
from ..host_integration import optional_host_integration_status


@dataclass(frozen=True)
class ProjectInitializationError(Exception):
    code: str


_DETERMINISTIC_ARTIFACTS = (
    "process-forge.yaml",
    "assignments/first-assignment.yaml",
    "artifacts/project-onboarding-report.md",
)


def _resource_state(items: Any) -> dict[str, int]:
    count = len(items) if isinstance(items, list) else 0
    return {"required": 0, "recommended": 0, "activated": count, "missing": 0}


def entry_status(project_root: Path) -> dict[str, Any]:
    """Entry ownership and budget confidence never replace context health."""
    try:
        return entry_migration.check_entry(project_root)
    except (EntryError, OSError) as exc:
        return {"status": "conflict", "entry": "unverified", "budget": {"status": "budget_unverified"},
                "blockers": [exc.reason if isinstance(exc, EntryError) else "storage_error"]}


def plan_agent_entry(project_root: Path, budget_policy: Any = None) -> dict[str, Any]:
    try:
        return entry_migration.plan_entry(project_root, budget_policy=budget_policy)
    except (EntryError, OSError) as exc:
        raise ProjectInitializationError(exc.reason if isinstance(exc, EntryError) else "storage_error") from exc


def apply_agent_entry(project_root: Path, plan: dict[str, Any]) -> dict[str, Any]:
    """Apply only a preflighted entry plan; retain incomplete recovery receipts."""
    try:
        receipt = entry_migration.apply_entry(project_root, plan, apply=True)
    except (EntryError, OSError) as exc:
        raise ProjectInitializationError(exc.reason if isinstance(exc, EntryError) else "storage_error") from exc
    complete = receipt.get("action") in {"applied", "unchanged"}
    return {"status": "complete" if complete else "blocked", "agent_entry": receipt,
            "next_action": "continue" if complete else "rollback_agent_entry_transaction"}


def _create_project_root(project_root: Path) -> None:
    # Validate the existing ancestor before acknowledged greenfield creation;
    # resolving the input first would erase a symlink/junction boundary.
    ancestor = project_root
    while not ancestor.exists() and ancestor != ancestor.parent:
        ancestor = ancestor.parent
    try:
        entry_migration.root_path(ancestor)
        project_root.mkdir(parents=True, exist_ok=True)
    except (EntryError, OSError) as exc:
        raise ProjectInitializationError(exc.reason if isinstance(exc, EntryError) else "storage_error") from exc


def status(project_root: Path, core: Any, *, workplace: str | None = None) -> dict[str, Any]:
    """Return a non-mutating, public-safe initialization read model."""
    project_root = Path(project_root).expanduser().absolute()
    flow = project_root / ".pf"
    snapshot_path, _snapshot_md = core.project_context_snapshot_paths(project_root)
    context = core.project_context_check_result(project_root, explicit_workplace=workplace) if flow.is_dir() else {"status": "missing"}
    health = context.get("health") if isinstance(context.get("health"), dict) else {}
    snapshot = core.load_yaml_document(snapshot_path) if snapshot_path.is_file() else {}
    resolved = snapshot.get("resolved") if isinstance(snapshot.get("resolved"), dict) else {}
    missing_artifacts = [item for item in _DETERMINISTIC_ARTIFACTS if not (flow / item).is_file()] if flow.is_dir() else list(_DETERMINISTIC_ARTIFACTS)
    codex = optional_host_integration_status(project_root, core)
    if not flow.is_dir() or not snapshot_path.is_file():
        state = "incomplete"
    elif str(health.get("status") or "") == "blocked":
        state = "blocked"
    elif str(context.get("status") or "") in {"stale", "broken"} or missing_artifacts:
        state = "repairable"
    else:
        state = "complete"
    workplace_path = Path(workplace).expanduser() if workplace else None
    if workplace_path is None:
        workplace_state = "auto"
    elif not workplace_path.exists():
        workplace_state = "missing"
    elif workplace_path.is_dir() and not (workplace_path / "workplace.yaml").is_file():
        workplace_state = "unreachable"
    else:
        workplace_state = "reachable"
    mcp_rows = resolved.get("activated_mcp") or resolved.get("available_mcp") or []
    entry = entry_status(project_root)
    repair_plan = []
    if state == "incomplete":
        repair_plan.append("initialize")
    if state == "repairable":
        repair_plan.append("refresh_context")
        if missing_artifacts:
            repair_plan.append("restore_deterministic_artifacts")
    if state != "incomplete" and entry.get("status") == "planned":
        repair_plan.append("migrate_agent_entry")
    return {"schema_version": 1, "kind": "pf.project_initialization.status", "state": state, "snapshot": {"status": context.get("status"), "health": health.get("status")}, "snapshot_health": health.get("status"), "workplace": workplace_state, "resources": {"knowledge": _resource_state(resolved.get("knowledge_resources")), "tools": _resource_state(resolved.get("tools")), "mcp": _resource_state(mcp_rows), "templates": _resource_state(resolved.get("templates"))}, "mcp": "active_in_snapshot" if mcp_rows else "not_configured", "codex_integration": codex, "agent_entry": entry, "missing_deterministic_artifacts": missing_artifacts, "repair_plan": repair_plan or ["none"], "public_safety": "no_private_paths"}


def apply(action: str, *, apply_requested: Any, execute: Callable[[], dict[str, Any]]) -> dict[str, Any]:
    """Execute a supplied writer only after an exact explicit acknowledgement."""
    if apply_requested is not True:
        raise ProjectInitializationError("apply_required")
    result = execute()
    return {"action": action, "applied": True, "result": result}


def _initialization_request(request: dict[str, Any], core: Any) -> dict[str, Any]:
    raw_root, raw_workplace = request.get("project_root"), request.get("workplace")
    if not raw_root or not raw_workplace:
        raise ProjectInitializationError("project_root_and_workplace_required")
    project_root = Path(str(raw_root)).expanduser().absolute()
    workplace = Path(str(raw_workplace)).expanduser().resolve()
    if workplace.is_dir():
        workplace = workplace / "workplace.yaml"
    answers_path = request.get("answers_path")
    answers = core.load_answers(Path(str(answers_path)).expanduser().resolve() if answers_path else None)
    supplied_answers = request.get("answers")
    if isinstance(supplied_answers, dict):
        answers.update(supplied_answers)
    project_type = request.get("project_type")
    if project_type:
        project_answers = answers.get("project") if isinstance(answers.get("project"), dict) else {}
        project_answers["type"] = str(project_type)
        answers["project"] = project_answers
    coordination_mode = request.get("coordination_mode")
    if coordination_mode:
        coordination_answers = answers.get("coordination") if isinstance(answers.get("coordination"), dict) else {}
        coordination_answers["mode"] = str(coordination_mode)
        answers["coordination"] = coordination_answers
    platforms = [str(item) for item in request.get("platforms", []) if str(item)] if isinstance(request.get("platforms"), list) else []
    if platforms:
        project_answers = answers.get("project") if isinstance(answers.get("project"), dict) else {}
        project_answers["platforms"] = platforms
        answers["project"] = project_answers
    specializations = [str(item) for item in request.get("specializations", []) if str(item)] if isinstance(request.get("specializations"), list) else []
    if specializations:
        answers["specializations"] = specializations
    process_id = str(request.get("process") or "").strip()
    if process_id:
        answers["process"] = process_id
    return {"project_root": project_root, "workplace": workplace, "answers": answers, "project_type": str(project_type) if project_type else None, "coordination_mode": str(coordination_mode) if coordination_mode else None, "force": bool(request.get("force", False)), "allow_missing_workplace": bool(request.get("allow_missing_workplace", False)), "command": str(request.get("command") or "project-onboard")}


def initialize_project(request: dict[str, Any], core: Any) -> dict[str, Any]:
    """Plan or perform one deterministic initialization workflow for CLI and MCP."""
    normalized = _initialization_request(request, core)
    project_root, workplace = normalized["project_root"], normalized["workplace"]
    apply_requested = request.get("apply")
    if apply_requested is True and not workplace.is_file() and not normalized["allow_missing_workplace"]:
        raise ProjectInitializationError("workplace_manifest_required")
    if apply_requested is not True and not project_root.is_dir():
        raise ProjectInitializationError("project_root_missing")
    if apply_requested is True:
        _create_project_root(project_root)
    entry_plan = plan_agent_entry(project_root, request.get("entry_budget_policy"))
    normalized["agent_entry_plan"] = entry_plan
    if apply_requested is True and entry_plan["blockers"]:
        raise ProjectInitializationError(entry_plan["blockers"][0])
    files = core.build_project_files(project_root, workplace, normalized["answers"])
    if apply_requested is True:
        return apply("initialize", apply_requested=True, execute=lambda: core.execute_project_initialization(normalized, files))
    planned = [core.rel(path, project_root) for path in files]
    planned.extend(f"{core.PROJECT_FLOW_ROOT}/{item}" for item in core.PROJECT_FLOW_DIRS)
    planned.append(".gitignore")
    if apply_requested is not True:
        return {"action": "initialize", "applied": False, "status": "blocked" if entry_plan["blockers"] else "planned", "mode": core.project_mode(project_root, normalized["answers"]), "planned_artifacts": sorted(set(planned)), "agent_entry": entry_plan, "next_action": "resolve_entry_blockers" if entry_plan["blockers"] else "rerun with apply: true"}
    raise ProjectInitializationError("apply_required")


def repair_project(request: dict[str, Any], core: Any) -> dict[str, Any]:
    """Repair deterministic project state only; it never performs onboarding."""
    raw_root = request.get("project_root")
    if not raw_root:
        raise ProjectInitializationError("project_root_required")
    project_root = Path(str(raw_root)).expanduser().absolute()
    if not project_root.is_dir() or not (project_root / ".pf").is_dir():
        raise ProjectInitializationError("project_not_initialized")
    action = str(request.get("repair_action") or "refresh_context")
    if action not in {"refresh_context", "restore_deterministic_artifacts", "migrate_agent_entry", "install_codex_hooks"}:
        raise ProjectInitializationError("unsupported_repair_action")
    workplace = request.get("workplace")
    before = status(project_root, core, workplace=str(workplace) if workplace else None)
    entry_plan = None
    if action in {"restore_deterministic_artifacts", "migrate_agent_entry"}:
        entry_plan = plan_agent_entry(project_root, request.get("entry_budget_policy"))
        if request.get("apply") is True and entry_plan["blockers"]:
            raise ProjectInitializationError(entry_plan["blockers"][0])
    if request.get("apply") is not True:
        blocked = bool(entry_plan and entry_plan["blockers"])
        return {"action": "repair", "applied": False, "status": "blocked" if blocked else "planned", "repair_action": action, "before": {"state": before["state"], "snapshot": before["snapshot"], "agent_entry": before["agent_entry"]}, "agent_entry": entry_plan, "next_action": "resolve_entry_blockers" if blocked else "rerun with apply: true"}
    if action == "migrate_agent_entry":
        return apply("repair", apply_requested=True, execute=lambda: apply_agent_entry(project_root, entry_plan))
    if action == "restore_deterministic_artifacts":
        def restore() -> dict[str, Any]:
            manifest = core.load_yaml_document(project_root / ".pf" / "process-forge.yaml")
            answers = {key: manifest[key] for key in ("project", "coordination", "context_requirements", "context_policy", "parameters", "specializations", "process") if isinstance(manifest, dict) and key in manifest}
            platforms = manifest.get("platform_contracts") if isinstance(manifest, dict) and isinstance(manifest.get("platform_contracts"), list) else []
            project_answers = answers.get("project") if isinstance(answers.get("project"), dict) else {}
            project_answers["platforms"] = [str(item.get("id") or item.get("platform") or "") for item in platforms if isinstance(item, dict) and str(item.get("id") or item.get("platform") or "")]
            answers["project"] = project_answers
            files = core.build_project_files(project_root, Path(str(workplace)).expanduser().resolve() / "workplace.yaml" if workplace and Path(str(workplace)).is_dir() else Path(str(workplace)).expanduser().resolve() if workplace else core.resolve_workplace_manifest(project_root / ".pf" / "process-forge.local.yaml"), answers)
            return core.execute_project_initialization({"project_root": project_root, "project_type": project_answers.get("type"), "force": False, "command": "project-init-repair", "agent_entry_plan": entry_plan}, files)
        return apply("repair", apply_requested=True, execute=restore)
    if action == "install_codex_hooks":
        if not hasattr(core, "execute_project_codex_integration_repair"):
            raise ProjectInitializationError("codex_integration_unsupported")
        return apply("repair", apply_requested=True, execute=lambda: core.execute_project_codex_integration_repair(project_root))
    return apply("repair", apply_requested=True, execute=lambda: core.execute_project_repair(project_root, workplace=str(workplace) if workplace else None, reason=str(request.get("reason") or "manual")))


def initialize(*, apply_requested: Any, execute: Callable[[], dict[str, Any]]) -> dict[str, Any]:
    return apply("initialize", apply_requested=apply_requested, execute=execute)


def repair(*, apply_requested: Any, execute: Callable[[], dict[str, Any]]) -> dict[str, Any]:
    return apply("repair", apply_requested=apply_requested, execute=execute)
