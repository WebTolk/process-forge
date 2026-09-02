"""Lazy local Runtime host PoC built on existing ProcessForge Core functions.

The Runtime host keeps only rebuildable handles and session routing cache in
workplace runtime state. Durable project facts remain in existing `.pf` files.
"""

from __future__ import annotations

import argparse
import contextlib
import hashlib
import io
import json
import os
import threading
import uuid
from pathlib import Path
from typing import Any

from . import RUNTIME_PROTOCOL_VERSION
from .raw_ingress_kernel import NativeAgentEvent, RawIngressKernel, deterministic_derived_key


# One Runtime process may serve several concurrent loopback requests.  This
# lock protects the read-modify-write cache and event-deduplication sequence;
# durable authority still belongs to the existing PF Core files.
STATE_LOCK = threading.RLock()
PROCESS_DEFINITION_CACHE: dict[tuple[str, str], tuple[Path, int, dict[str, Any]]] = {}
PENDING_CONVERSATION_CAPTURES: dict[tuple[str, str], dict[str, tuple[dict[str, Any], Any]]] = {}


def state_lock() -> threading.RLock:
    return STATE_LOCK


def state_path(workplace_root: Path) -> Path:
    return workplace_root / "runtime" / "pf-runtime-host" / "state.json"


def projection_path(project_root: Path, core: Any) -> Path:
    return core.locate_flow_root(project_root) / "artifacts" / "projections" / "command-history.md"


def stage_obligations_path(project_root: Path, core: Any) -> Path:
    return core.locate_flow_root(project_root) / "artifacts" / "projections" / "stage-obligations.json"


def content_hash(payload: Any) -> str:
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return "sha256:" + hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def output_fact(project_root: Path, output: dict[str, Any], core: Any) -> dict[str, Any]:
    output_id = str(output.get("id") or "output")
    path = core.task_output_path(project_root, output)
    if path is None:
        return {"id": output_id, "status": "invalid", "path": "", "reason": "required output has no path"}
    if not path.is_file():
        return {"id": output_id, "status": "missing", "path": core.rel(path, project_root)}
    stat = path.stat()
    return {
        "id": output_id,
        "status": "present",
        "path": core.rel(path, project_root),
        "size": stat.st_size,
        "sha256": "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest(),
    }


def journal_events(project_root: Path, core: Any) -> list[dict[str, Any]]:
    path, _outbox = core.event_runtime_paths(project_root)
    if not path.is_file():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            item = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(item, dict):
            rows.append(item)
    return rows


def execution_stage(task: dict[str, Any], run_state: dict[str, Any], process: dict[str, Any]) -> str:
    """Resolve a Stage from durable task/run state and a Process declaration.

    Runtime never invents stage names: an assignment may declare `stage`, and a
    process may explicitly map durable worker statuses for its own runtime
    boundary. Unknown or invalid values deliberately remain empty.
    """
    if str(task.get("status") or "") in {"done", "completed", "cancelled", "failed"}:
        return ""
    stages = process.get("stages") if isinstance(process.get("stages"), list) else []
    stage_ids = {str(item.get("id") or "") for item in stages if isinstance(item, dict)}
    declared = str(task.get("stage") or "")
    if declared in stage_ids:
        return declared
    boundary = process.get("runtime_execution_boundary") if isinstance(process.get("runtime_execution_boundary"), dict) else {}
    by_status = boundary.get("stage_by_worker_status") if isinstance(boundary.get("stage_by_worker_status"), dict) else {}
    mapped = str(by_status.get(str(run_state.get("status") or "")) or "")
    return mapped if mapped in stage_ids else ""


def resolved_process(project_root: Path, process_id: str, core: Any) -> dict[str, Any] | None:
    """Resolve a process once, then invalidate only when its declaration changes."""
    resolved_project_root = project_root.resolve()
    key = (str(resolved_project_root), process_id)
    cached = PROCESS_DEFINITION_CACHE.get(key)
    if cached is not None:
        path, modified_ns, process = cached
        try:
            if path.is_file() and path.stat().st_mtime_ns == modified_ns:
                return process
        except OSError:
            pass
    try:
        from processforge_core.process_catalog import (
            ProcessCatalogContext,
            resolve_process_definition as resolve_process_definition_core,
        )

        workplace_manifest = core.resolve_project_workplace_manifest(resolved_project_root)
        context = ProcessCatalogContext(
            project_root=resolved_project_root,
            flow_root=core.locate_flow_root(resolved_project_root),
            distribution_root=core.ROOT.resolve(),
            active_official_pack_ids=frozenset(core.active_process_pack_ids(workplace_manifest)),
        )
        definition = resolve_process_definition_core(context, process_id)
    except SystemExit:
        return None
    try:
        modified_ns = definition.path.stat().st_mtime_ns
    except OSError:
        modified_ns = -1
    process = definition.process
    PROCESS_DEFINITION_CACHE[key] = (definition.path, modified_ns, process)
    return process


def declared_stage_obligations(project_root: Path, core: Any) -> list[dict[str, Any]]:
    """Read technical obligations from process definitions, never from Runtime policy."""
    flow_root = core.locate_flow_root(project_root)
    results: list[dict[str, Any]] = []
    process_cache: dict[str, dict[str, Any] | None] = {}
    for assignment_path in sorted((flow_root / "assignments").glob("*.yaml")):
        task = core.load_yaml_document(assignment_path)
        if not isinstance(task, dict) or not task.get("id"):
            continue
        process_id = core.task_process_id(task)
        if not process_id:
            continue
        if process_id not in process_cache:
            process_cache[process_id] = resolved_process(project_root, process_id, core)
        process = process_cache[process_id]
        if not process:
            continue
        run_id = str(task.get("run_id") or "")
        run_state = core.load_agent_run_state(project_root, run_id, str(task.get("id"))) if run_id else {}
        stage_id = execution_stage(task, run_state, process)
        stages = process.get("stages") if isinstance(process.get("stages"), list) else []
        stage = next((item for item in stages if isinstance(item, dict) and str(item.get("id") or "") == stage_id), None)
        obligations = stage.get("automation_bindings") if isinstance(stage, dict) and isinstance(stage.get("automation_bindings"), list) else []
        if not obligations and isinstance(stage, dict) and isinstance(stage.get("technical_obligations"), list):
            obligations = stage["technical_obligations"]
        for obligation in obligations:
            if isinstance(obligation, dict) and str(obligation.get("projector") or ""):
                results.append({"task": task, "run_state": run_state, "process_id": process_id, "stage_id": stage_id, "process": process, "obligation": obligation})
    return results


def required_outputs_for_task(project_root: Path, task: dict[str, Any], core: Any) -> list[dict[str, Any]]:
    required = [output_fact(project_root, output, core) for output in core.normalize_required_outputs(task.get("required_outputs")) if bool(output.get("required", True))]
    expected = task.get("expected_report") if isinstance(task.get("expected_report"), dict) else {}
    expected_path = str(expected.get("artifact") or "")
    if expected_path:
        required.append(output_fact(project_root, {"id": "expected-report", "path": expected_path}, core))
    return required


def obligation_base(item: dict[str, Any], required: list[dict[str, Any]], core: Any) -> dict[str, Any]:
    task = item["task"]
    obligation = item["obligation"]
    return {
        "id": f"{item['process_id']}:{item['stage_id']}:{obligation.get('id') or 'obligation'}:{task['id']}",
        "projector": str(obligation.get("projector") or ""),
        "task_id": str(task["id"]),
        "run_id": str(task.get("run_id") or ""),
        "process_id": item["process_id"],
        "stage_id": item["stage_id"],
        "obligation_id": str(obligation.get("id") or "obligation"),
        "gate": str(obligation.get("gate") or ""),
        "required_outputs": required,
    }


def build_required_output_readiness(item: dict[str, Any], project_root: Path, core: Any) -> dict[str, Any]:
    task = item["task"]
    required = required_outputs_for_task(project_root, task, core)
    statuses = {str(output.get("status") or "") for output in required}
    readiness = "invalid" if "invalid" in statuses else ("missing" if "missing" in statuses else "ready")
    row = obligation_base(item, required, core)
    row["readiness"] = readiness
    row["source_fingerprint"] = content_hash({"assignment": task, "worker_state": item["run_state"], "required_outputs": required, "process": item["process"], "obligation": item["obligation"]})
    return row


def declared_verification_event(project_root: Path, task_id: str, verification: dict[str, Any], core: Any) -> dict[str, Any] | None:
    passed_event = str(verification.get("passed_event") or "")
    failed_event = str(verification.get("failed_event") or "")
    for event in reversed(journal_events(project_root, core)):
        event_type = str(event.get("event_type") or "")
        assignment = event.get("assignment") if isinstance(event.get("assignment"), dict) else {}
        if event_type in {passed_event, failed_event} and (str(assignment.get("id") or "") == task_id or str(event.get("subject") or "") == task_id):
            return event
    return None


def build_verification_state(item: dict[str, Any], project_root: Path, core: Any) -> dict[str, Any]:
    task = item["task"]
    obligation = item["obligation"]
    verification = obligation.get("verification") if isinstance(obligation.get("verification"), dict) else {}
    required = required_outputs_for_task(project_root, task, core)
    event = declared_verification_event(project_root, str(task["id"]), verification, core)
    passed_event = str(verification.get("passed_event") or "")
    failed_event = str(verification.get("failed_event") or "")
    event_type = str(event.get("event_type") or "") if event else ""
    result = "passed" if event_type == passed_event else ("failed" if event_type == failed_event else "not_run")
    event_data = event.get("data") if event and isinstance(event.get("data"), dict) else {}
    current_inputs = core.task_verification_fingerprint(project_root, task)
    evidence_inputs = str(event_data.get("verification_fingerprint") or "")
    readiness = "ready" if result == "passed" and evidence_inputs == current_inputs else ("stale" if result == "passed" and evidence_inputs else ("missing" if result == "passed" else ("invalid" if result == "failed" else "missing")))
    row = obligation_base(item, required, core)
    row["readiness"] = readiness
    row["verification"] = {"result": result, "event_id": str(event.get("event_id") or "") if event else "", "event_type": event_type, "time": str(event.get("time") or "") if event else "", "input_fingerprint": evidence_inputs}
    row["source_fingerprint"] = content_hash({"assignment": task, "required_outputs": required, "process": item["process"], "obligation": obligation, "verification": verification, "event": event or {}, "current_inputs": current_inputs})
    return row


PROJECTOR_BUILDERS = {"required-output-readiness": build_required_output_readiness, "verification-state": build_verification_state}


def stage_obligation_rows(project_root: Path, core: Any) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for item in declared_stage_obligations(project_root, core):
        builder = PROJECTOR_BUILDERS.get(str(item["obligation"].get("projector") or ""))
        if builder is not None:
            rows.append(builder(item, project_root, core))
    return rows


def rebuild_stage_obligations(project_root: Path, core: Any) -> Path:
    rows = stage_obligation_rows(project_root, core)
    payload = {
        "schema_version": 1,
        "kind": "stage-obligations",
        "generated_at": core.now_utc(),
        "project_id": core.project_id(project_root),
        "source": {"event_journal": core.rel(core.event_runtime_paths(project_root)[0], project_root), "authority": "process-definitions+durable-assignments+inspector-state"},
        "obligations": rows,
    }
    out = stage_obligations_path(project_root, core)
    write_json(out, payload)
    return out


def stage_obligations_payload(project_root: Path, core: Any) -> dict[str, Any]:
    path = stage_obligations_path(project_root, core)
    if not path.is_file():
        return {"status": "missing", "path": core.rel(path, project_root), "obligations": []}
    try:
        stored = read_json(path)
    except (OSError, json.JSONDecodeError):
        return {"status": "invalid", "path": core.rel(path, project_root), "obligations": []}
    if str(stored.get("kind") or "") != "stage-obligations" or not isinstance(stored.get("obligations"), list):
        return {"status": "invalid", "path": core.rel(path, project_root), "obligations": []}
    projected: list[dict[str, Any]] = []
    for row in stored["obligations"]:
        if not isinstance(row, dict):
            continue
        readiness = str(row.get("readiness") or "invalid")
        freshness = "current" if readiness == "ready" else readiness
        try:
            task = core.load_task(project_root, str(row.get("task_id") or ""))
            for output in row.get("required_outputs") if isinstance(row.get("required_outputs"), list) else []:
                if isinstance(output, dict):
                    current = output_fact(project_root, {"id": output.get("id"), "path": output.get("path")}, core)
                    if current.get("status") != output.get("status") or current.get("sha256") != output.get("sha256"):
                        freshness = "stale"
            verification = row.get("verification") if isinstance(row.get("verification"), dict) else {}
            if verification and str(verification.get("input_fingerprint") or "") != core.task_verification_fingerprint(project_root, task):
                freshness = "stale"
        except (OSError, SystemExit, ValueError):
            freshness = "stale"
        projected.append({**row, "freshness": freshness})
    status = "current"
    if any(row.get("freshness") == "invalid" for row in projected):
        status = "invalid"
    elif any(row.get("freshness") == "missing" for row in projected):
        status = "missing"
    elif any(row.get("freshness") == "stale" for row in projected):
        status = "stale"
    return {"status": status, "path": core.rel(path, project_root), "generated_at": stored.get("generated_at"), "obligations": projected}


def read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{os.getpid()}.{uuid.uuid4().hex}.tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def call_quiet(func: Any, args: argparse.Namespace) -> int:
    with contextlib.redirect_stdout(io.StringIO()):
        return int(func(args) or 0)


def load_state(workplace_root: Path) -> dict[str, Any]:
    payload = read_json(state_path(workplace_root))
    if not payload:
        payload = {
            "schema_version": 1,
            "runtime_protocol_version": RUNTIME_PROTOCOL_VERSION,
            "status": "lazy",
            "projects": [],
            "sessions": {},
        }
    payload.setdefault("schema_version", 1)
    payload.setdefault("runtime_protocol_version", RUNTIME_PROTOCOL_VERSION)
    payload.setdefault("status", "lazy")
    payload.setdefault("projects", [])
    payload.setdefault("sessions", {})
    return payload


def save_state(workplace_root: Path, state: dict[str, Any], core: Any) -> None:
    state["updated_at"] = core.now_utc()
    state["workplace_root"] = str(workplace_root)
    state["processforge_core_version"] = getattr(core, "PROCESSFORGE_VERSION", "")
    write_json(state_path(workplace_root), state)


def event_exists(project_root: Path, event_id: str, core: Any) -> bool:
    events_path, _outbox = core.event_runtime_paths(project_root)
    if not events_path.is_file():
        return False
    for line in events_path.read_text(encoding="utf-8", errors="replace").splitlines():
        if not line.strip():
            continue
        try:
            item = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(item, dict) and core.event_id_value(item) == event_id:
            return True
    return False


def stable_event_id(payload: dict[str, Any]) -> str:
    raw = payload.get("event_id") or payload.get("id")
    if raw:
        text = str(raw)
        return text if text.startswith("evt_") else "evt_" + hashlib.sha256(text.encode("utf-8")).hexdigest()[:32]
    basis = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    return "evt_" + hashlib.sha256(basis.encode("utf-8")).hexdigest()


def resolve_workplace(args: argparse.Namespace, project_root: Path | None, core: Any) -> Path:
    return core.resolve_workplace_root(getattr(args, "workplace", None), project_root=project_root)


def resolve_project(project_ref: str, core: Any) -> Path:
    project_root = Path(project_ref).expanduser().resolve()
    core.require_flow_root(project_root)
    return project_root


def route_project(project_ref: str, workplace_root: Path, core: Any) -> dict[str, Any]:
    project_root = resolve_project(project_ref, core)
    manifest = core.locate_flow_root(project_root) / "process-forge.yaml"
    if not manifest.is_file():
        raise SystemExit(f"FAIL: project is not ProcessForge-onboarded: {project_root}")
    coordination = core.effective_project_coordination(project_root, str(workplace_root))
    project_key = core.project_id(project_root)
    return {
        "project_id": project_key,
        "project_root": str(project_root),
        "flow_root": core.flow_label(project_root),
        "effective_mode": coordination.get("effective_mode", "simple"),
        "director_enabled": bool(coordination.get("director_available") and coordination.get("effective_mode") == "organized"),
    }


def remember_project(state: dict[str, Any], handle: dict[str, Any]) -> None:
    projects = [item for item in state.get("projects", []) if isinstance(item, dict) and item.get("project_id") != handle["project_id"]]
    projects.append(handle)
    state["projects"] = sorted(projects, key=lambda item: str(item.get("project_id") or ""))


def remember_session(state: dict[str, Any], session_id: str, handle: dict[str, Any], agent_id: str, core: Any) -> None:
    if not session_id:
        return
    sessions = state.setdefault("sessions", {})
    sessions[session_id] = {
        "cache_only": True,
        "agent_id": agent_id,
        "session_id": session_id,
        "project_id": handle["project_id"],
        "project_root": handle["project_root"],
        "last_seen_at": core.now_utc(),
    }


def ledger_session(session_id: str, workplace_root: Path, core: Any) -> dict[str, Any]:
    """Return the Core-owned session record; Runtime state is never authority."""
    if not session_id:
        return {}
    core.update_stale_agent_presence(workplace_root)
    return core.find_agent_presence(workplace_root, session_id=session_id)


def load_input(args: argparse.Namespace) -> dict[str, Any]:
    value = getattr(args, "input", None)
    if not value or value == "-":
        text = input()
    else:
        text = Path(value).read_text(encoding="utf-8")
    data = json.loads(text)
    if not isinstance(data, dict):
        raise SystemExit("FAIL: runtime event input must be a JSON object")
    return data


def normalize_event(raw: dict[str, Any], project_root: Path, core: Any) -> dict[str, Any]:
    event_type = str(raw.get("event_type") or raw.get("type") or "")
    if not event_type:
        raise SystemExit("FAIL: runtime event input missing event_type")
    source = raw.get("source") if isinstance(raw.get("source"), dict) else {}
    adapter = str(source.get("adapter") or raw.get("adapter") or "generic")
    agent_id = str(source.get("agent") or raw.get("agent_id") or raw.get("agent") or "agent")
    session_id = str(source.get("session_id") or raw.get("session_id") or "")
    run_id = str(raw.get("run_id") or "")
    task_id = str(raw.get("task_id") or "")
    subject = str(raw.get("subject") or task_id or run_id or session_id or event_type)
    data = raw.get("payload") if isinstance(raw.get("payload"), dict) else raw.get("data")
    if not isinstance(data, dict):
        data = {}
    if run_id and "run_id" not in data:
        data["run_id"] = run_id
    if task_id and "task_id" not in data:
        data["task_id"] = task_id
    event = core.processforge_event(
        project_root,
        event_type,
        session_id=session_id or None,
        assignment_id_value=task_id or None,
        subject=subject,
        data=data,
        correlation_id=str(raw.get("correlation_id") or session_id or run_id or ""),
        event_id=stable_event_id(raw),
        actor={"type": "agent", "id": core.safe_id(agent_id, "agent"), "role": str(raw.get("role") or "")},
    )
    event["source"] = f"processforge.runtime.{core.safe_id(adapter, 'adapter')}"
    return event


def ledger_from_event(raw: dict[str, Any], project_root: Path, workplace_root: Path, handle: dict[str, Any], core: Any) -> None:
    event_type = str(raw.get("event_type") or raw.get("type") or "")
    source = raw.get("source") if isinstance(raw.get("source"), dict) else {}
    agent_id = str(source.get("agent") or raw.get("agent_id") or raw.get("agent") or "agent")
    session_id = str(source.get("session_id") or raw.get("session_id") or "")
    role = raw.get("role") or source.get("role") or []
    roles = [role] if isinstance(role, str) and role else [str(item) for item in role] if isinstance(role, list) else []
    common = {
        "workplace": str(workplace_root),
        "project_root": str(project_root),
        "agent": agent_id,
        "session": session_id,
        "process": str(raw.get("process_id") or ""),
        "run": str(raw.get("run_id") or ""),
        "task": str(raw.get("task_id") or ""),
    }
    if event_type in {"agent.session.started", "agent.session.resumed"}:
        call_quiet(core.command_agent_checkin, argparse.Namespace(**common, project_id=handle["project_id"], role=roles, capability=[], supports_specialization=[], ttl=int(raw.get("ttl") or 300), json=False))
    elif event_type in {"agent.heartbeat", "agent.command.completed", "agent.tool.completed"} and session_id:
        presence = core.find_agent_presence(workplace_root, agent_id=agent_id, session_id=session_id)
        if presence:
            call_quiet(core.command_agent_heartbeat, argparse.Namespace(**common))
    elif event_type in {"agent.session.ended", "agent.session.stopped"} and session_id:
        presence = core.find_agent_presence(workplace_root, agent_id=agent_id, session_id=session_id)
        if presence:
            call_quiet(core.command_agent_checkout, argparse.Namespace(**common))


def rebuild_projection(project_root: Path, core: Any) -> Path:
    with state_lock():
        events_path, _outbox = core.event_runtime_paths(project_root)
        rows: list[dict[str, Any]] = []
        if events_path.is_file():
            for line in events_path.read_text(encoding="utf-8", errors="replace").splitlines():
                if not line.strip():
                    continue
                try:
                    item = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if isinstance(item, dict) and str(item.get("event_type") or "").startswith("agent."):
                    rows.append(item)
        out = projection_path(project_root, core)
        lines = [
            "# Runtime Command History",
            "",
            f"- source: `{core.rel(events_path, project_root)}`",
            f"- generated_at: `{core.now_utc()}`",
            "",
            "| time | event | actor | session | subject | status |",
            "| --- | --- | --- | --- | --- | --- |",
        ]
        for item in rows:
            data = item.get("data") if isinstance(item.get("data"), dict) else {}
            actor = item.get("actor") if isinstance(item.get("actor"), dict) else {}
            session = item.get("session") if isinstance(item.get("session"), dict) else {}
            status = data.get("status") or data.get("exit_code") or ""
            lines.append(
                "| {time} | `{event}` | `{actor}` | `{session}` | `{subject}` | `{status}` |".format(
                    time=str(item.get("time") or ""),
                    event=str(item.get("event_type") or ""),
                    actor=str(actor.get("id") or ""),
                    session=str(session.get("id") or ""),
                    subject=str(item.get("subject") or ""),
                    status=str(status),
                )
            )
        out.parent.mkdir(parents=True, exist_ok=True)
        tmp = out.with_name(f".{out.name}.{os.getpid()}.{uuid.uuid4().hex}.tmp")
        tmp.write_text("\n".join(lines) + "\n", encoding="utf-8")
        os.replace(tmp, out)
        return out


def command_init(args: argparse.Namespace, core: Any) -> int:
    project_roots = [resolve_project(value, core) for value in getattr(args, "project_root", [])]
    workplace_root = resolve_workplace(args, project_roots[0] if project_roots else None, core)
    with state_lock():
        state = load_state(workplace_root)
        for project_root in project_roots:
            remember_project(state, route_project(str(project_root), workplace_root, core))
        save_state(workplace_root, state, core)
    print(f"RUNTIME_HOST: initialized projects={len(state.get('projects', []))}")
    return 0


def command_event(args: argparse.Namespace, core: Any) -> int:
    raw = load_input(args)
    workplace_root = resolve_workplace(args, None, core) if getattr(args, "workplace", None) else None
    payload = ingest_event(raw, workplace_root, core, project_ref=getattr(args, "project_root", None))
    if getattr(args, "json", False):
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(f"EVENT: {payload['event_id']} duplicate={str(payload['duplicate']).lower()} project={payload['project_id']}")
    return 0


def _ingest_derived_event(raw: dict[str, Any], workplace_root: Path | None, core: Any, *, project_ref: str | None = None) -> dict[str, Any]:
    project_ref = project_ref or raw.get("project_root") or raw.get("cwd")
    if not project_ref:
        raise SystemExit("FAIL: runtime event requires --project-root or project_root/cwd in input")
    project_root = resolve_project(str(project_ref), core)
    workplace_root = workplace_root or core.resolve_workplace_root(None, project_root=project_root)
    with state_lock():
        handle = route_project(str(project_root), workplace_root, core)
        state = load_state(workplace_root)
        source = raw.get("source") if isinstance(raw.get("source"), dict) else {}
        session_id = str(source.get("session_id") or raw.get("session_id") or "")
        event_type = str(raw.get("event_type") or raw.get("type") or "")
        if session_id:
            presence = ledger_session(session_id, workplace_root, core)
            if presence:
                if str(presence.get("project_id") or "") != handle["project_id"]:
                    raise PermissionError("session is not authorized for requested project_root")
            elif event_type not in {"agent.session.started", "agent.session.resumed"}:
                raise PermissionError(f"runtime session is not routed: {session_id}")
        remember_project(state, handle)
        event = normalize_event(raw, project_root, core)
        duplicate = event_exists(project_root, core.event_id_value(event), core)
        if not duplicate:
            ledger_from_event(raw, project_root, workplace_root, handle, core)
            core.append_process_event(project_root, event)
        remember_session(state, session_id, handle, str(source.get("agent") or raw.get("agent_id") or raw.get("agent") or ""), core)
        save_state(workplace_root, state, core)
        projection = rebuild_projection(project_root, core)
        stage_projection = rebuild_stage_obligations(project_root, core)
        payload = {"event_id": core.event_id_value(event), "duplicate": duplicate, "project_id": handle["project_id"], "events": core.rel(core.event_runtime_paths(project_root)[0], project_root), "projection": core.rel(projection, project_root), "stage_projection": core.rel(stage_projection, project_root)}
        return payload


def _is_native_envelope(raw: dict[str, Any]) -> bool:
    return bool(
        raw.get("provider")
        and raw.get("adapter")
        and raw.get("native_event_type")
        and isinstance(raw.get("raw_payload"), dict)
    )


def _runtime_native_envelope(raw: dict[str, Any], project_ref: str | None) -> dict[str, Any]:
    """Wrap legacy normalized Runtime input without changing its derived ID."""

    source = raw.get("source") if isinstance(raw.get("source"), dict) else {}
    return {
        "provider": "processforge",
        "adapter": str(source.get("adapter") or raw.get("adapter") or "runtime-legacy"),
        "native_event_type": str(raw.get("event_type") or raw.get("type") or "runtime.event"),
        "raw_payload": dict(raw),
        "native_event_id": raw.get("event_id"),
        "native_id_scope": "adapter",
        "native_event_id_stable": bool(raw.get("event_id")),
        "source_session_id": str(source.get("session_id") or raw.get("session_id") or "") or None,
        "source_project_ref": str(project_ref or raw.get("project_root") or raw.get("cwd") or "") or None,
        "derived_event": dict(raw),
    }


def _raw_receipt_payload(receipt: Any) -> dict[str, Any]:
    return {
        "raw_event_id": receipt.raw_event_id,
        "accepted": receipt.accepted,
        "deduplicated": receipt.deduplicated,
        "raw_location": receipt.raw_location,
        "routing_status": receipt.routing_status,
        "normalized_event_ids": list(receipt.normalized_event_ids),
        "chat_message_ids": list(receipt.chat_message_ids),
        "diagnostics": dict(receipt.diagnostics),
    }


def _conversation_denial(reason: str, **details: Any) -> tuple[list[str], dict[str, Any]]:
    return [], {"conversation": {"status": "denied", "reason": reason, **details}}


def _conversation_deferred(reason: str, **details: Any) -> tuple[list[str], dict[str, Any]]:
    return [], {"conversation": {"status": "deferred", "reason": reason, **details}}


def _conversation_reason(diagnostics: dict[str, Any]) -> str:
    conversation = diagnostics.get("conversation") if isinstance(diagnostics.get("conversation"), dict) else {}
    return str(conversation.get("reason") or "")


def _is_worker_conversation(envelope: dict[str, Any]) -> bool:
    return str(envelope.get("provider") or "") == "processforge" and str(envelope.get("adapter") or "") == "pf-codex-exec-worker"


def _pending_conversation_key(project_root: Path, session_id: str, core: Any) -> tuple[str, str]:
    return (core.project_id(project_root), session_id)


def _pending_conversation_state_key(project_root: Path, session_id: str, core: Any) -> str:
    project_id = core.project_id(project_root)
    digest = hashlib.sha256(json.dumps({"project_id": project_id, "session_id": session_id}, sort_keys=True).encode("utf-8")).hexdigest()
    return "pending_" + digest[:32]


def _defer_conversation_capture(envelope: dict[str, Any], receipt: Any, project_root: Path, workplace_root: Path, core: Any) -> None:
    session_id = str(envelope.get("source_session_id") or "")
    raw_id = str(receipt.raw_event_id or "")
    if not session_id or not raw_id:
        return
    with state_lock():
        pending = PENDING_CONVERSATION_CAPTURES.setdefault(_pending_conversation_key(project_root, session_id, core), {})
        pending[raw_id] = (dict(envelope), receipt)
        state = load_state(workplace_root)
        durable = state.setdefault("pending_conversation_captures", {})
        session_key = _pending_conversation_state_key(project_root, session_id, core)
        session_pending = durable.setdefault(
            session_key,
            {
                "project_id": core.project_id(project_root),
                "session_id": session_id,
                "items": {},
            },
        )
        items = session_pending.setdefault("items", {})
        items[raw_id] = {"raw_event_id": raw_id, "envelope": dict(envelope)}
        save_state(workplace_root, state, core)


def _flush_deferred_conversation(
    project_root: Path, workplace_root: Path, session_id: str, core: Any
) -> tuple[list[str], dict[str, Any]]:
    if not session_id:
        return [], {}
    with state_lock():
        memory_key = _pending_conversation_key(project_root, session_id, core)
        queued = dict(PENDING_CONVERSATION_CAPTURES.get(memory_key, {}))
        state = load_state(workplace_root)
        durable = state.setdefault("pending_conversation_captures", {})
        session_key = _pending_conversation_state_key(project_root, session_id, core)
        stored = durable.get(session_key, {})
    stored_items = stored.get("items") if isinstance(stored, dict) and isinstance(stored.get("items"), dict) else {}
    for raw_id, item in stored_items.items():
        if raw_id in queued or not isinstance(item, dict) or not isinstance(item.get("envelope"), dict):
            continue
        queued[str(raw_id)] = (dict(item["envelope"]), argparse.Namespace(raw_event_id=str(item.get("raw_event_id") or raw_id)))
    if not queued:
        return [], {}
    identifiers: list[str] = []
    failures: list[dict[str, Any]] = []
    succeeded: list[str] = []
    for raw_id, (envelope, receipt) in queued.items():
        chat_ids, diagnostics = _conversation_messages(envelope, receipt, project_root, workplace_root, core)
        identifiers.extend(chat_ids)
        reason = _conversation_reason(diagnostics)
        if reason:
            failures.append({"raw_event_id": raw_id, "reason": reason})
        else:
            succeeded.append(raw_id)
    if succeeded:
        with state_lock():
            memory_pending = PENDING_CONVERSATION_CAPTURES.get(_pending_conversation_key(project_root, session_id, core), {})
            for raw_id in succeeded:
                memory_pending.pop(raw_id, None)
            if not memory_pending:
                PENDING_CONVERSATION_CAPTURES.pop(_pending_conversation_key(project_root, session_id, core), None)
            state = load_state(workplace_root)
            durable = state.setdefault("pending_conversation_captures", {})
            session_key = _pending_conversation_state_key(project_root, session_id, core)
            stored = durable.get(session_key, {})
            stored_items = stored.get("items") if isinstance(stored, dict) and isinstance(stored.get("items"), dict) else {}
            for raw_id in succeeded:
                stored_items.pop(raw_id, None)
            if isinstance(stored, dict) and stored_items:
                stored["items"] = stored_items
                durable[session_key] = stored
            else:
                durable.pop(session_key, None)
            save_state(workplace_root, state, core)
    diagnostics: dict[str, Any] = {"deferred_conversation": {"flushed": len(queued), "chat_message_ids": identifiers}}
    if failures:
        diagnostics["deferred_conversation"]["failures"] = failures
    return identifiers, diagnostics


def _derived_event_type(raw: dict[str, Any]) -> str:
    return str(raw.get("event_type") or raw.get("type") or "")


def _derived_session_id(raw: dict[str, Any]) -> str:
    source = raw.get("source") if isinstance(raw.get("source"), dict) else {}
    return str(source.get("session_id") or raw.get("session_id") or "")


def _is_safe_automatic_content(content: str) -> bool:
    # Marker names may appear in a safe worker report that explains which
    # private values were withheld. Reject their values (via secret/path
    # checks below), not the vocabulary used to describe that policy.
    return not bool(__import__("re").search(r"(?:[a-zA-Z]:[\\/]|/(?:users|home|tmp|var)/)", content))


def worker_input_summary(run_id: str, task_id: str, attempt: str, payload_hash: str, expected_report: str) -> str:
    return (
        f"ProcessForge launched worker run `{run_id}`, task `{task_id}`, attempt `{attempt}`; "
        f"stdin_payload_hash=`{payload_hash}`; expected_report=`{expected_report}`."
    )


def _worker_input_contract(envelope: dict[str, Any], project_root: Path, core: Any) -> dict[str, Any] | None:
    raw = envelope.get("raw_payload") if isinstance(envelope.get("raw_payload"), dict) else {}
    run_id, task_id, attempt = (str(raw.get(key) or "") for key in ("run_id", "task_id", "attempt"))
    payload = raw.get("stdin_payload")
    payload_hash = str(raw.get("stdin_payload_hash") or "")
    expected_report = str(raw.get("expected_report") or "")
    if not run_id or not task_id or not attempt or not isinstance(payload, str) or not payload_hash or not expected_report:
        return None
    if payload_hash != "sha256:" + hashlib.sha256(payload.encode("utf-8")).hexdigest():
        return None
    contract_path = project_root / ".pf" / "runtime" / "agent-runs" / core.safe_id(run_id, "run") / core.safe_id(task_id, "task") / "worker-input-contract.json"
    try:
        contract = json.loads(contract_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    required = {"run_id": run_id, "task_id": task_id, "attempt": attempt, "stdin_payload_hash": payload_hash, "expected_report": expected_report}
    if any(str(contract.get(key) or "") != value for key, value in required.items()):
        return None
    summary = worker_input_summary(run_id, task_id, attempt, payload_hash, expected_report)
    if str(contract.get("summary") or "") != summary:
        return None
    return {**required, "summary": summary}


def _allowed_conversation_message(envelope: dict[str, Any], item: dict[str, Any]) -> bool:
    provider, adapter, event_type = (str(envelope.get(key) or "") for key in ("provider", "adapter", "native_event_type"))
    role = str(item.get("message_role") or "")
    source = item.get("content_source") if isinstance(item.get("content_source"), dict) else {}
    kind, provenance = str(source.get("kind") or ""), str(source.get("content_provenance") or "")
    raw = envelope.get("raw_payload") if isinstance(envelope.get("raw_payload"), dict) else {}
    session = str(envelope.get("source_session_id") or "")
    if (provider, adapter, event_type, role, kind, provenance) == ("codex", "codex-hooks", "UserPromptSubmit", "user", "codex_hook", "provider_payload"):
        return isinstance(raw.get("prompt"), str) and item.get("content") == raw.get("prompt")
    if (provider, adapter, event_type, role, kind, provenance) in {
        ("codex", "codex-hooks", "Stop", "assistant", "codex_hook", "provider_payload"),
        ("codex", "codex-hooks", "SubagentStop", "assistant", "codex_hook", "provider_payload"),
        ("codex", "codex-hooks", "SessionEnd", "assistant", "codex_hook", "provider_payload"),
    }:
        return isinstance(raw.get("last_assistant_message"), str) and item.get("content") == raw.get("last_assistant_message") and str(item.get("session_id") or session) == session
    if provider != "processforge" or adapter != "pf-codex-exec-worker":
        return False
    run_id, task_id, attempt = (str(raw.get(key) or "") for key in ("run_id", "task_id", "attempt"))
    if session != f"pf-worker:{run_id}:{task_id}:attempt:{attempt}":
        return False
    if event_type == "WorkerPromptPayloadSubmitted":
        return (
            (role, kind, provenance) == ("system", "pf_codex_exec_input", "pf_owned_safe_summary")
            and str(envelope.get("native_event_id") or "") == f"worker-input:{run_id}:{task_id}:attempt:{attempt}"
            and item.get("content") == worker_input_summary(run_id, task_id, attempt, str(raw.get("stdin_payload_hash") or ""), str(raw.get("expected_report") or ""))
        )
    if event_type == "WorkerExpectedReportCaptured":
        report_content = raw.get("report_content")
        report_hash = "sha256:" + hashlib.sha256(report_content.encode("utf-8")).hexdigest() if isinstance(report_content, str) else ""
        return (
            (role, kind, provenance) == ("assistant", "pf_codex_exec_output", "pf_owned_output_file")
            and str(envelope.get("native_event_id") or "") == f"worker-output:{run_id}:{task_id}:attempt:{attempt}:{report_hash}"
            and item.get("content") == report_content
        )
    return False


def _worker_session_authorized(envelope: dict[str, Any], project_root: Path, core: Any) -> bool:
    raw = envelope.get("raw_payload") if isinstance(envelope.get("raw_payload"), dict) else {}
    run_id, task_id = str(raw.get("run_id") or ""), str(raw.get("task_id") or "")
    if not run_id or not task_id:
        return False
    try:
        task = core.load_task(project_root, task_id)
    except (OSError, SystemExit):
        return False
    if str(task.get("run_id") or "") != run_id:
        return False
    state = core.load_agent_run_state(project_root, run_id, task_id)
    attempt = str(raw.get("attempt") or "")
    if not state or attempt != str(state.get("attempt") or ""):
        return False
    expected = task.get("expected_report") if isinstance(task.get("expected_report"), dict) else {}
    expected_report = str(expected.get("artifact") or "")
    if str(raw.get("expected_report") or "") != expected_report:
        return False
    if str(envelope.get("native_event_type") or "") == "WorkerPromptPayloadSubmitted" and _worker_input_contract(envelope, project_root, core) is None:
        return False
    if str(envelope.get("native_event_type") or "") == "WorkerExpectedReportCaptured":
        report = project_root / expected_report
        if not report.is_file() or report.read_text(encoding="utf-8", errors="replace") != raw.get("report_content"):
            return False
    return True


def _is_session_end_fallback_duplicate(envelope: dict[str, Any], item: dict[str, Any], project_root: Path, core: Any) -> bool:
    if str(envelope.get("provider") or "") != "codex" or str(envelope.get("adapter") or "") != "codex-hooks":
        return False
    if str(envelope.get("native_event_type") or "") != "SessionEnd" or str(item.get("message_role") or "") != "assistant":
        return False
    content = item.get("content")
    turn_id = str(item.get("turn_id") or "")
    session_id = str(envelope.get("source_session_id") or "")
    if not isinstance(content, str) or not content.strip() or not session_id:
        return False
    for existing in core.load_chat_messages(project_root, session_id):
        body = existing.get("message") if isinstance(existing.get("message"), dict) else {}
        participant = existing.get("participant") if isinstance(existing.get("participant"), dict) else {}
        existing_primary = str(participant.get("id") or "") == "codex" or str(participant.get("type") or "") == "subagent"
        if (
            (not turn_id or str(existing.get("turn_id") or "") == turn_id)
            and existing_primary
            and body.get("role") == "assistant"
            and body.get("content") == content
        ):
            return True
    return False


def _conversation_messages(
    envelope: dict[str, Any],
    receipt: Any,
    project_root: Path,
    workplace_root: Path,
    core: Any,
    *,
    ended_session_presence: dict[str, Any] | None = None,
) -> tuple[list[str], dict[str, Any]]:
    messages = envelope.get("derived_conversation_messages")
    if messages is None:
        return [], {}
    if not isinstance(messages, list):
        return _conversation_denial("messages_not_list")
    session_id = str(envelope.get("source_session_id") or "")
    if not session_id:
        return _conversation_denial("missing_session")
    is_worker = _is_worker_conversation(envelope)
    presence = ledger_session(session_id, workplace_root, core)
    if is_worker:
        authorized = _worker_session_authorized(envelope, project_root, core)
    else:
        active_presence = presence or ended_session_presence or {}
        authorized = bool(active_presence) and str(active_presence.get("project_id") or "") == core.project_id(project_root)
    if not authorized:
        return _conversation_denial("session_not_authorized", session_id=session_id)
    identifiers: list[str] = []
    for sequence, item in enumerate(messages):
        if not isinstance(item, dict):
            return _conversation_denial("message_not_object", sequence=sequence)
        content = item.get("content")
        role = str(item.get("message_role") or "")
        participant = item.get("participant") if isinstance(item.get("participant"), dict) else {}
        source = item.get("content_source") if isinstance(item.get("content_source"), dict) else {}
        if not isinstance(content, str) or not content.strip() or role not in {"user", "assistant", "system"}:
            return _conversation_denial("invalid_message", sequence=sequence)
        if not _allowed_conversation_message(envelope, item):
            return _conversation_denial("untrusted_conversation_provenance", sequence=sequence)
        if _is_session_end_fallback_duplicate(envelope, item, project_root, core):
            continue
        if not _is_safe_automatic_content(content) or not _is_safe_automatic_content(json.dumps(source, ensure_ascii=False, sort_keys=True)) or core.contains_secret_value(content):
            return _conversation_denial("unsafe_automatic_content", sequence=sequence)
        raw_id = str(receipt.raw_event_id or "")
        key = deterministic_derived_key(
            raw_id,
            "conversation_message",
            f"processforge.conversation-capture.{envelope['adapter']}",
            "1",
            {
                "session_id": session_id,
                "turn_id": str(item.get("turn_id") or raw_id),
                "message_role": role,
                "delivery_sequence": int((item.get("delivery") or {}).get("sequence") or sequence),
                "content_hash": "sha256:" + hashlib.sha256(content.encode("utf-8")).hexdigest(),
            },
        )
        message_id = "msg_" + key[:32]
        event_id = "evt_" + hashlib.sha256(("chat.message.recorded:" + message_id).encode("utf-8")).hexdigest()[:32]
        _path, record, _event = core.append_chat_message(
            project_root,
            session_id=session_id,
            participant_id=str(participant.get("id") or envelope.get("adapter") or "agent"),
            participant_role=str(participant.get("role") or role),
            participant_type=str(participant.get("type") or "agent"),
            message_role=role,
            content=content,
            turn_id=str(item.get("turn_id") or raw_id),
            parent_message_id=str(item.get("parent_message_id") or "") or None,
            source_kind=str(source.get("kind") or "automatic_capture"),
            assignment_id_value=str((envelope.get("raw_payload") or {}).get("task_id") or "") or None,
            message_id=message_id,
            event_id=event_id,
        )
        identifiers.append(str(record.get("message_id") or message_id))
    return identifiers, {}


def ingest_event(raw: dict[str, Any], workplace_root: Path | None, core: Any, *, project_ref: str | None = None) -> dict[str, Any]:
    """Persist a private raw event before attempting its derived project effect.

    Adapters provide native envelopes and may attach an already-normalized
    ``derived_event``.  The Host remains provider-neutral: it only validates
    project scope and executes the existing normalized-event behavior.
    """

    envelope = dict(raw) if _is_native_envelope(raw) else _runtime_native_envelope(raw, project_ref)
    source_project_ref = str(envelope.get("source_project_ref") or project_ref or "")
    if not source_project_ref:
        raise SystemExit("FAIL: runtime event requires --project-root or project_root/cwd in input")
    project_root = resolve_project(source_project_ref, core)
    workplace_root = workplace_root or core.resolve_workplace_root(None, project_root=project_root)
    native = NativeAgentEvent(
        provider=str(envelope["provider"]),
        adapter=str(envelope["adapter"]),
        native_event_type=str(envelope["native_event_type"]),
        raw_payload=dict(envelope["raw_payload"]),
        payload_version=str(envelope.get("payload_version") or "1"),
        native_event_id=str(envelope.get("native_event_id") or "") or None,
        native_id_scope=str(envelope.get("native_id_scope") or "provider"),
        native_event_id_stable=bool(envelope.get("native_event_id_stable", True)),
        source_session_id=str(envelope.get("source_session_id") or "") or None,
        source_project_ref=source_project_ref,
    )
    receipt = RawIngressKernel(workplace_root).ingest(native)
    response = _raw_receipt_payload(receipt)
    if not receipt.accepted:
        return response

    derived = envelope.get("derived_event")
    derived_event_type = _derived_event_type(derived) if isinstance(derived, dict) else ""
    derived_session_id = _derived_session_id(derived) if isinstance(derived, dict) else ""
    ended_session_presence: dict[str, Any] | None = None
    if (
        isinstance(derived, dict)
        and derived_event_type in {"agent.session.ended", "agent.session.stopped"}
        and isinstance(envelope.get("derived_conversation_messages"), list)
        and derived_session_id
    ):
        ended_session_presence = ledger_session(derived_session_id, workplace_root, core)

    if isinstance(derived, dict):
        derived_ref = str(derived.get("project_root") or derived.get("cwd") or "")
        if derived_ref and resolve_project(derived_ref, core) != project_root:
            raise PermissionError("derived event project_root does not match native envelope")
        # Preserve the established CLI/Runtime 403 behavior for project/session
        # denial.  The raw receipt already exists at this point for later audit.
        routed = _ingest_derived_event(derived, workplace_root, core, project_ref=str(project_root))
        response = {
            **routed,
            **response,
            "routing_status": "routed",
            "normalized_event_ids": [str(routed["event_id"])],
        }
        if derived_event_type in {"agent.session.started", "agent.session.resumed"}:
            flushed_ids, flushed_diagnostics = _flush_deferred_conversation(project_root, workplace_root, derived_session_id, core)
            response["chat_message_ids"] = [*response["chat_message_ids"], *flushed_ids]
            response["diagnostics"] = {**response["diagnostics"], **flushed_diagnostics}

    chat_message_ids, conversation_diagnostics = _conversation_messages(
        envelope,
        receipt,
        project_root,
        workplace_root,
        core,
        ended_session_presence=ended_session_presence,
    )
    if (
        _conversation_reason(conversation_diagnostics) == "session_not_authorized"
        and not _is_worker_conversation(envelope)
        and derived_event_type not in {"agent.session.ended", "agent.session.stopped"}
        and str(envelope.get("source_session_id") or "")
        and not ledger_session(str(envelope.get("source_session_id") or ""), workplace_root, core)
    ):
        _defer_conversation_capture(envelope, receipt, project_root, workplace_root, core)
        chat_message_ids, conversation_diagnostics = _conversation_deferred(
            "session_not_authorized",
            session_id=str(envelope.get("source_session_id") or ""),
        )
    response["chat_message_ids"] = [*response["chat_message_ids"], *chat_message_ids]
    response["diagnostics"] = {**response["diagnostics"], **conversation_diagnostics}
    return response


def command_status(args: argparse.Namespace, core: Any) -> int:
    project_roots = [resolve_project(value, core) for value in getattr(args, "project_root", [])]
    workplace_root = resolve_workplace(args, project_roots[0] if project_roots else None, core)
    payload = status_payload(workplace_root, project_roots, core)
    if getattr(args, "json", False):
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(f"RUNTIME_HOST: projects={len(payload['projects'])} sessions={len(payload['sessions'])} ledger_sessions={payload['ledger_sessions']}")
    return 0


def status_payload(workplace_root: Path, project_roots: list[Path], core: Any) -> dict[str, Any]:
    with state_lock():
        state = load_state(workplace_root)
        for project_root in project_roots:
            remember_project(state, route_project(str(project_root), workplace_root, core))
        core.update_stale_agent_presence(workplace_root)
        payload = {
            "schema_version": 1,
            "runtime_protocol_version": RUNTIME_PROTOCOL_VERSION,
            "status": "lazy",
            "pid": os.getpid(),
            "workplace_root": str(workplace_root),
            "projects": state.get("projects", []),
            "sessions": state.get("sessions", {}),
            "ledger_sessions": len(core.iter_agent_presence(workplace_root)),
        }
        save_state(workplace_root, state, core)
        return payload


def project_for_session(args: argparse.Namespace, workplace_root: Path, core: Any) -> Path:
    session_id = getattr(args, "session", None)
    if getattr(args, "project_root", None):
        return resolve_project(getattr(args, "project_root"), core)
    if not session_id:
        raise SystemExit("FAIL: --session or --project-root is required")
    presence = ledger_session(str(session_id), workplace_root, core)
    project_ref = str(presence.get("project_root") or "") if presence else ""
    if not project_ref:
        raise SystemExit(f"FAIL: runtime session is not routed by Agent Ledger: {session_id}")
    project_root = resolve_project(project_ref, core)
    if str(presence.get("project_id") or "") != core.project_id(project_root):
        raise SystemExit(f"FAIL: Agent Ledger project binding is invalid: {session_id}")
    return project_root


def command_project_state(args: argparse.Namespace, core: Any) -> int:
    workplace_root = resolve_workplace(args, None, core)
    payload = project_state_payload(workplace_root, core, session=getattr(args, "session", None), project_root_ref=getattr(args, "project_root", None))
    print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) if getattr(args, "json", False) else core.dump_yaml(payload))
    return 0


def project_state_payload(workplace_root: Path, core: Any, *, session: str | None = None, project_root_ref: str | None = None) -> dict[str, Any]:
    project_root = project_for_session(argparse.Namespace(session=session, project_root=project_root_ref), workplace_root, core)
    handle = route_project(str(project_root), workplace_root, core)
    context = core.project_context_check_result(project_root, explicit_workplace=str(workplace_root))
    return {"project": handle, "context_status": context.get("status"), "policy_action": (context.get("policy") or {}).get("action")}


def active_execution_records(project_root: Path, core: Any) -> list[dict[str, Any]]:
    """Return current execution facts directly from durable assignments and run state."""
    flow_root = core.locate_flow_root(project_root)
    records: list[dict[str, Any]] = []
    process_cache: dict[str, dict[str, Any] | None] = {}
    for assignment_path in sorted((flow_root / "assignments").glob("*.yaml")):
        task = core.load_yaml_document(assignment_path)
        if not isinstance(task, dict) or not task.get("id"):
            continue
        task_status = str(task.get("status") or "")
        if task_status in {"done", "completed", "cancelled", "failed"}:
            continue
        process_id = core.task_process_id(task)
        if process_id not in process_cache:
            process_cache[process_id] = resolved_process(project_root, process_id, core) if process_id else None
        process = process_cache[process_id]
        run_id = str(task.get("run_id") or "")
        run_state = core.load_agent_run_state(project_root, run_id, str(task["id"])) if run_id else {}
        stage_id = execution_stage(task, run_state, process) if process else ""
        worker_status = str(run_state.get("status") or "")
        priority = 0 if worker_status == "running" else (1 if task_status in {"in_progress", "debugging", "review", "blocked"} else 2)
        records.append(
            {
                "process_id": process_id,
                "stage_id": stage_id,
                "run_id": run_id,
                "task_id": str(task["id"]),
                "assignment": core.rel(assignment_path, project_root),
                "task_status": task_status,
                "worker_status": worker_status,
                "priority": priority,
                "stage": next((item for item in process.get("stages", []) if isinstance(item, dict) and str(item.get("id") or "") == stage_id), {}) if process and stage_id else {},
            }
        )
    return sorted(records, key=lambda item: (item["priority"], item["run_id"], item["task_id"]))


def command_work_state(args: argparse.Namespace, core: Any) -> int:
    workplace_root = resolve_workplace(args, None, core)
    payload = work_state_payload(workplace_root, core, session=getattr(args, "session", None), project_root_ref=getattr(args, "project_root", None))
    print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) if getattr(args, "json", False) else core.dump_yaml(payload))
    return 0


def work_state_payload(workplace_root: Path, core: Any, *, session: str | None = None, project_root_ref: str | None = None) -> dict[str, Any]:
    from processforge_core.process_execution import ProcessExecutionService

    project_root = project_for_session(argparse.Namespace(session=session, project_root=project_root_ref), workplace_root, core)
    handle = route_project(str(project_root), workplace_root, core)
    events_path, _outbox = core.event_runtime_paths(project_root)
    supervisor = core.json_read(core.supervisor_state_path(project_root))
    projection = stage_obligations_payload(project_root, core)
    obligations = projection.get("obligations") if isinstance(projection.get("obligations"), list) else []
    execution = active_execution_records(project_root, core)
    active = execution[0] if execution else {}
    active_stage = active.get("stage") if isinstance(active.get("stage"), dict) else {}
    event_rows = journal_events(project_root, core)
    current_work_state = {
        "project": handle["project_id"],
        "active_sessions": [str(item.get("session_id") or "") for item in core.iter_agent_presence(workplace_root) if str(item.get("project_id") or "") == handle["project_id"]],
        "active_process": str(active.get("process_id") or ""),
        "active_stage": str(active.get("stage_id") or ""),
        "run": str(active.get("run_id") or ""),
        "task": str(active.get("task_id") or ""),
        "assignment": str(active.get("task_id") or ""),
        "workers": [{"task_id": str(row.get("task_id") or ""), "run_id": str(row.get("run_id") or ""), "status": str(row.get("worker_status") or "")} for row in execution],
        "stage_contract": {
            "entry_gates": list(active_stage.get("entry_gates") or []) if isinstance(active_stage.get("entry_gates"), list) else [],
            "exit_gates": list(active_stage.get("exit_gates") or []) if isinstance(active_stage.get("exit_gates"), list) else [],
        } if active_stage else {},
        "automation_bindings": obligations,
        "blockers": [],
        "execution": execution,
        "freshness": projection.get("status"),
        "last_relevant_activity": str(event_rows[-1].get("time") or "") if event_rows else "",
    }
    declarative_state = ProcessExecutionService(project_root, workplace_root, core).state(session_id=str(session or ""))
    if declarative_state.get("action") != "start_recommended":
        current_work_state.update(
            {
                "active_process": str(declarative_state.get("process", {}).get("id") or current_work_state["active_process"]),
                "active_stage": str(declarative_state.get("stage", {}).get("id") or current_work_state["active_stage"]),
                "run": str(declarative_state.get("run", {}).get("id") or current_work_state["run"]),
                "task": str(declarative_state.get("assignment", {}).get("id") or current_work_state["task"]),
                "assignment": str(declarative_state.get("assignment", {}).get("id") or current_work_state["assignment"]),
                "stage_contract": {
                    "entry_gates": declarative_state.get("gates", {}).get("entry", []),
                    "exit_gates": declarative_state.get("gates", {}).get("exit", []),
                },
                "automation_bindings": declarative_state.get("obligations", []),
                "freshness": "pinned",
                "process_execution": declarative_state,
            }
        )
    return {
        "project": handle,
        "current_session": core.read_current_project_session(project_root),
        "agent_presence": [item for item in core.iter_agent_presence(workplace_root) if str(item.get("project_id") or "") == handle["project_id"]],
        "events_path": core.rel(events_path, project_root),
        "event_count": len(events_path.read_text(encoding="utf-8", errors="replace").splitlines()) if events_path.is_file() else 0,
        "supervisor": supervisor,
        "projections": {"stage_obligations": projection},
        "current_work_state": current_work_state,
    }


def command_resolve(args: argparse.Namespace, core: Any) -> int:
    workplace_root = resolve_workplace(args, None, core)
    payload = resolve_payload(workplace_root, core, session=getattr(args, "session", None), project_root_ref=getattr(args, "project_root", None))
    print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) if getattr(args, "json", False) else core.dump_yaml(payload))
    return 0


def resolve_payload(workplace_root: Path, core: Any, *, session: str | None = None, project_root_ref: str | None = None, resource_id: str | None = None) -> dict[str, Any]:
    from processforge_core.garage import ResourceResolveService

    project_root = project_for_session(argparse.Namespace(session=session, project_root=project_root_ref), workplace_root, core)
    handle = route_project(str(project_root), workplace_root, core)
    resolved_payload = ResourceResolveService(project_root, workplace_root, core).resolve(resource_id=resource_id)
    payload: dict[str, Any] = {"workplace_root": str(workplace_root), "project": handle, "session": session or ""}
    if not resource_id:
        return payload
    return {**payload, "resource": resolved_payload.get("resource", {})}


def workplace_state_payload(workplace_root: Path, core: Any) -> dict[str, Any]:
    core.update_stale_agent_presence(workplace_root)
    presence = core.iter_agent_presence(workplace_root)
    projects: dict[str, dict[str, Any]] = {}
    for item in presence:
        project_id = str(item.get("project_id") or "")
        if project_id:
            projects.setdefault(project_id, {"project_id": project_id, "sessions": 0, "online": 0})["sessions"] += 1
            if item.get("status") == "online":
                projects[project_id]["online"] += 1
    return {"workplace_root": str(workplace_root), "agent_ledger": presence, "projects": sorted(projects.values(), key=lambda item: item["project_id"]), "runtime_cache": "derived"}


def command_tick(args: argparse.Namespace, core: Any) -> int:
    project_roots = [resolve_project(value, core) for value in getattr(args, "project_root", [])]
    if not project_roots:
        raise SystemExit("FAIL: runtime-host tick requires at least one --project-root")
    workplace_root = resolve_workplace(args, project_roots[0], core)
    payload, status = tick_payload(workplace_root, project_roots, core, director=getattr(args, "director", False), inspector=getattr(args, "inspector", False), run=getattr(args, "run", None), profile=getattr(args, "profile", None), driver=getattr(args, "driver", None), wait_ttl=getattr(args, "wait_ttl", 3600), lease_ttl=getattr(args, "lease_ttl", 3600))
    print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) if getattr(args, "json", False) else core.dump_yaml(payload))
    return status


def tick_payload(
    workplace_root: Path,
    project_roots: list[Path],
    core: Any,
    *,
    director: bool = False,
    inspector: bool = False,
    run: str | None = None,
    profile: str | None = None,
    driver: str | None = None,
    wait_ttl: int = 3600,
    lease_ttl: int = 3600,
) -> tuple[dict[str, Any], int]:
    with state_lock():
        state = load_state(workplace_root)
        core.update_stale_agent_presence(workplace_root)
        results: list[dict[str, Any]] = []
        status = 0
        for project_root in project_roots:
            handle = route_project(str(project_root), workplace_root, core)
            remember_project(state, handle)
            item: dict[str, Any] = {"project_id": handle["project_id"], "effective_mode": handle["effective_mode"], "director": "skipped", "inspector": "skipped"}
            if director:
                if handle["effective_mode"] == "organized":
                    rc = call_quiet(core.command_agent_director_tick, argparse.Namespace(workplace=str(workplace_root), project_root=str(project_root), project_id=handle["project_id"], wait_ttl=wait_ttl, lease_ttl=lease_ttl))
                    item["director"] = "tick"
                    status = status or rc
                else:
                    item["director"] = "skipped_simple"
            if inspector:
                rc = call_quiet(core.command_supervisor_tick, argparse.Namespace(project_root=str(project_root), run=run, profile=profile, driver=driver, start_allowed=False))
                item["inspector"] = "tick"
                status = status or rc
            stage_projection = rebuild_stage_obligations(project_root, core)
            item["projection"] = core.rel(stage_projection, project_root)
            results.append(item)
        save_state(workplace_root, state, core)
        payload = {"status": "ok" if status == 0 else "failed", "projects": results}
        return payload, status


def command_rebuild_projections(args: argparse.Namespace, core: Any) -> int:
    project_roots = [resolve_project(value, core) for value in getattr(args, "project_root", [])]
    outputs = [
        {
            "project_id": core.project_id(project_root),
            "projection": core.rel(rebuild_projection(project_root, core), project_root),
            "stage_projection": core.rel(rebuild_stage_obligations(project_root, core), project_root),
        }
        for project_root in project_roots
    ]
    print(json.dumps({"projections": outputs}, ensure_ascii=False, indent=2, sort_keys=True) if getattr(args, "json", False) else core.dump_yaml({"projections": outputs}))
    return 0


def command_projection_doctor(args: argparse.Namespace, core: Any) -> int:
    project_roots = [resolve_project(value, core) for value in getattr(args, "project_root", [])]
    checks: list[Any] = []
    for project_root in project_roots:
        payload = stage_obligations_payload(project_root, core)
        label = core.project_id(project_root)
        rows = payload.get("obligations") if isinstance(payload.get("obligations"), list) else []
        failed_verification = next((row for row in rows if isinstance(row, dict) and isinstance(row.get("verification"), dict) and str(row["verification"].get("result") or "") != "passed"), None)
        if failed_verification is not None:
            checks.append(core.check("FAIL", f"{label} verification obligation is {failed_verification['verification'].get('result')}"))
        elif payload["status"] == "current":
            checks.append(core.check("PASS", f"{label} stage obligations projection is current"))
        elif payload["status"] == "missing":
            checks.append(core.check("FAIL", f"{label} stage obligations projection has missing required output"))
        elif payload["status"] == "stale":
            checks.append(core.check("FAIL", f"{label} stage obligations projection is stale"))
        else:
            checks.append(core.check("FAIL", f"{label} stage obligations projection is invalid"))
    return core.print_checks(checks)
