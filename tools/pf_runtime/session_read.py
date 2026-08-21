"""Bounded, Ledger-authorized session read models for the PF MCP facade.

This is the common Runtime read layer.  It owns response shaping and keeps the
stdio MCP adapter transport-only; durable project and Ledger facts remain in
the existing ProcessForge Core files.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from . import host


MAX_CHAT_LIMIT = 100
MAX_ACTIVITY_LIMIT = 100
MAX_CONTEXT_ACTIVITY = 20


@dataclass(frozen=True)
class SessionReadError(Exception):
    """A stable, non-diagnostic error exposed by the MCP surface."""

    code: str


def _bounded_limit(value: Any, *, default: int, maximum: int) -> int:
    if value is None:
        return default
    if isinstance(value, bool):
        raise SessionReadError("invalid_limit")
    try:
        limit = int(value)
    except (TypeError, ValueError) as exc:
        raise SessionReadError("invalid_limit") from exc
    if not 1 <= limit <= maximum:
        raise SessionReadError("invalid_limit")
    return limit


def _authorized_project(
    workplace_root: Path, core: Any, session_id: str, project_root_ref: Any = None
) -> tuple[Path, dict[str, Any]]:
    if not session_id:
        raise SessionReadError("missing_session")
    # Read models must not mutate stale-presence status or emit Ledger expiry
    # events. A direct Core lookup is the authority for this access check.
    presence = core.find_agent_presence(workplace_root, session_id=session_id)
    if not presence:
        raise SessionReadError("unknown_session")
    project_ref = str(presence.get("project_root") or "")
    if not project_ref:
        raise SessionReadError("session_not_routed")
    try:
        project_root = host.resolve_project(project_ref, core)
    except SystemExit as exc:
        raise SessionReadError("session_project_invalid") from exc
    if str(presence.get("project_id") or "") != core.project_id(project_root):
        raise SessionReadError("session_project_invalid")
    if project_root_ref not in (None, ""):
        try:
            requested_project = host.resolve_project(str(project_root_ref), core)
        except SystemExit as exc:
            raise SessionReadError("invalid_project_root") from exc
        if core.project_id(requested_project) != core.project_id(project_root):
            raise SessionReadError("session_project_mismatch")
    return project_root, presence


def _project_summary(project_root: Path, workplace_root: Path, core: Any) -> dict[str, Any]:
    handle = host.route_project(str(project_root), workplace_root, core)
    return {
        "id": handle.get("project_id"),
        "coordination_mode": handle.get("effective_mode"),
        "flow_root": core.rel(core.locate_flow_root(project_root), project_root),
    }


def _activity_fact(event: dict[str, Any]) -> dict[str, Any]:
    assignment = event.get("assignment") if isinstance(event.get("assignment"), dict) else {}
    process = event.get("process") if isinstance(event.get("process"), dict) else {}
    actor = event.get("actor") if isinstance(event.get("actor"), dict) else {}
    return {
        "event_id": event.get("event_id"),
        "time": event.get("time"),
        "event_type": event.get("event_type"),
        "severity": event.get("severity"),
        "subject": event.get("subject"),
        "assignment_id": assignment.get("id"),
        "process_id": process.get("id"),
        "stage_id": process.get("stage_id"),
        "actor": {"id": actor.get("id"), "role": actor.get("role"), "type": actor.get("type")},
    }


def _session_activity_rows(project_root: Path, core: Any, session_id: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for event in host.journal_events(project_root, core):
        session = event.get("session") if isinstance(event.get("session"), dict) else {}
        if str(session.get("id") or "") == session_id:
            rows.append(_activity_fact(event))
    return rows


def session_context_payload(
    workplace_root: Path, core: Any, *, session_id: str, project_root_ref: Any = None
) -> dict[str, Any]:
    project_root, presence = _authorized_project(workplace_root, core, session_id, project_root_ref)
    execution = host.active_execution_records(project_root, core)
    active = execution[0] if execution else {}
    context = core.project_context_check_result(project_root, explicit_workplace=str(workplace_root))
    project_id = core.project_id(project_root)
    agents = [
        {
            "agent_id": item.get("agent_id"),
            "session_id": item.get("session_id"),
            "role": item.get("role"),
            "status": item.get("status"),
            "last_seen_at": item.get("last_seen_at"),
        }
        for item in core.iter_agent_presence(workplace_root)
        if str(item.get("project_id") or "") == project_id
    ]
    blockers = [
        {"kind": "assignment", "task_id": item.get("task_id"), "status": item.get("task_status")}
        for item in execution
        if str(item.get("task_status") or "") == "blocked"
    ]
    health = context.get("health") if isinstance(context.get("health"), dict) else {}
    if str(context.get("status") or "") not in {"fresh", "ok"}:
        blockers.append({"kind": "context", "status": context.get("status"), "health": health.get("status")})
    return {
        "schema_version": 1,
        "kind": "pf.session_context",
        "session": {
            "id": session_id,
            "agent_id": presence.get("agent_id"),
            "role": presence.get("role"),
            "status": presence.get("status"),
        },
        "project": _project_summary(project_root, workplace_root, core),
        "work": {
            "run_id": active.get("run_id"),
            "task_id": active.get("task_id"),
            "process_id": active.get("process_id"),
            "stage_id": active.get("stage_id"),
            "task_status": active.get("task_status"),
            "worker_status": active.get("worker_status"),
        },
        "blockers": blockers[:10],
        "active_agents": agents[:20],
        "context_freshness": {
            "status": context.get("status"),
            "policy_action": (context.get("policy") or {}).get("action") if isinstance(context.get("policy"), dict) else None,
            "health": health.get("status"),
        },
        # Context is authorized by the session, but must describe current
        # project work even when a durable fact was emitted by another active
        # project agent rather than this exact session.
        "recent_activity": list(reversed([_activity_fact(item) for item in host.journal_events(project_root, core)[-MAX_CONTEXT_ACTIVITY:]])),
    }


def session_chat_payload(
    workplace_root: Path,
    core: Any,
    *,
    session_id: str,
    project_root_ref: Any = None,
    limit: Any = None,
    before: Any = None,
    cursor: Any = None,
    roles: Any = None,
) -> dict[str, Any]:
    project_root, _presence = _authorized_project(workplace_root, core, session_id, project_root_ref)
    page_limit = _bounded_limit(limit, default=50, maximum=MAX_CHAT_LIMIT)
    if before not in (None, "") and cursor not in (None, "") and str(before) != str(cursor):
        raise SessionReadError("ambiguous_cursor")
    boundary = str(before or cursor or "")
    role_filter: set[str] = set()
    if roles is not None:
        if not isinstance(roles, list) or not all(isinstance(item, str) for item in roles):
            raise SessionReadError("invalid_roles")
        role_filter = set(roles)
        if not role_filter.issubset({"user", "assistant", "system"}):
            raise SessionReadError("invalid_roles")
    messages = core.load_chat_messages(project_root, session_id)
    if role_filter:
        messages = [item for item in messages if str((item.get("message") or {}).get("role") or "") in role_filter]
    end = len(messages)
    if boundary:
        matching = [index for index, item in enumerate(messages) if str(item.get("message_id") or "") == boundary]
        if not matching:
            raise SessionReadError("invalid_cursor")
        end = matching[0]
    start = max(0, end - page_limit)
    page = messages[start:end]
    return {
        "schema_version": 1,
        "kind": "pf.session_chat",
        "session_id": session_id,
        "messages": core.chat_export_messages(page, include_content=True),
        "page": {"limit": page_limit, "before": boundary or None, "next_before": str(messages[start].get("message_id") or "") if start > 0 and page else None},
    }


def session_activity_payload(
    workplace_root: Path, core: Any, *, session_id: str, project_root_ref: Any = None, limit: Any = None
) -> dict[str, Any]:
    project_root, _presence = _authorized_project(workplace_root, core, session_id, project_root_ref)
    page_limit = _bounded_limit(limit, default=50, maximum=MAX_ACTIVITY_LIMIT)
    # The caller is scoped by its Ledger session; activity is a current-project
    # read model, not a filter that hides work emitted by peer project agents.
    rows = [_activity_fact(item) for item in host.journal_events(project_root, core)]
    return {
        "schema_version": 1,
        "kind": "pf.session_activity",
        "session_id": session_id,
        "activity": list(reversed(rows[-page_limit:])),
        "bounded": {"limit": page_limit, "returned": min(len(rows), page_limit)},
    }
