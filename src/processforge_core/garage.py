"""Garage-level project context, search, and resolve services."""

from __future__ import annotations

import copy
import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .local_resource_search import LocalSearchError, ResourceSearchIndex
from .process_execution import ProcessExecutionService


@dataclass(frozen=True)
class ProjectContextService:
    project_root: Path
    workplace_root: Path
    core: Any

    def project_id(self) -> str:
        return str(self.core.project_id(self.project_root))

    def snapshot(self) -> dict[str, Any]:
        snapshot_path, _snapshot_md = self.core.project_context_snapshot_paths(self.project_root)
        return self.core.load_yaml_document(snapshot_path)

    def check(self) -> dict[str, Any]:
        return self.core.project_context_check_result(self.project_root, explicit_workplace=str(self.workplace_root))

    def runtime_snapshot(self) -> dict[str, Any]:
        return snapshot_with_resolved_search_roots(self.project_root, self.snapshot(), self.workplace_root, self.core)

    def context(self, *, session_id: str = "") -> dict[str, Any]:
        check = self.check()
        snapshot = self.snapshot() if not check.get("broken") else {}
        manifest = self.core.load_yaml_document(self.core.locate_flow_root(self.project_root) / "process-forge.yaml")
        search = ResourceSearchService(self.project_root, self.workplace_root, self.core).readiness(snapshot=snapshot, check=check)
        mode = GarageModeService(self.project_root, self.workplace_root, self.core).status(snapshot=snapshot, session_id=session_id)
        payload: dict[str, Any] = {
            "schema_version": 1,
            "kind": "pf.context",
            "mode": mode["mode"],
            "project": {
                "id": self.project_id(),
                "root": str(self.project_root),
            },
            "context": {
                "snapshot_id": check.get("snapshot_id"),
                "status": check.get("status"),
                "policy_action": check.get("policy_action"),
                "recommended_action": check.get("recommended_action"),
            },
            "process": {
                "id": str(manifest.get("process") or ""),
                "available": process_summary(snapshot),
            },
            "resources": {
                "search_status": search.get("status"),
                "reason": search.get("reason"),
                "resource_count": search.get("resource_count"),
                "document_count": search.get("document_count"),
                "search": search,
                "selection": resource_selection_summary(snapshot),
            },
            "work": CurrentWorkService(self.project_root, self.core).summary(),
            "derived_reports": DerivedReportLifecycleService(self.project_root, self.core).status(snapshot=snapshot),
            "session": mode["session"],
            "diagnostics": diagnostics_from_check(check, search, mode),
        }
        return payload


@dataclass(frozen=True)
class GarageModeService:
    project_root: Path
    workplace_root: Path
    core: Any

    def status(self, *, snapshot: dict[str, Any] | None = None, session_id: str = "") -> dict[str, Any]:
        snapshot = snapshot or load_snapshot(self.project_root, self.core)
        coordination = snapshot.get("workplace_coordination") if isinstance(snapshot.get("workplace_coordination"), dict) else {}
        effective_mode = str(coordination.get("effective_mode") or "simple")
        director_required = bool(coordination.get("director_required", effective_mode == "organized"))
        mode = "forge" if effective_mode == "organized" or director_required else "garage"
        blockers: list[dict[str, str]] = []
        if mode == "forge" and director_required and not bool(coordination.get("director_office_exists", False)):
            blockers.append({"code": "forge_runtime_required_but_unavailable", "message": "Project coordination requires Forge/Director runtime, but required runtime infrastructure is unavailable."})
        return {
            "mode": mode,
            "source": "project_coordination",
            "coordination": {
                "effective_mode": effective_mode,
                "director_required": director_required,
                "director_available_at_workplace": bool(coordination.get("director_available_at_workplace", False)),
                "director_office_exists": bool(coordination.get("director_office_exists", False)),
            },
            "session": {"status": "bound", "id": session_id} if session_id else {"status": "absent"},
            "blockers": blockers,
        }


@dataclass(frozen=True)
class ResourceSearchService:
    project_root: Path
    workplace_root: Path
    core: Any

    def readiness(self, *, snapshot: dict[str, Any] | None = None, check: dict[str, Any] | None = None) -> dict[str, Any]:
        check = check or self.core.project_context_check_result(self.project_root, explicit_workplace=str(self.workplace_root))
        if str(check.get("status") or "") not in {"fresh", "fresh_with_updates"}:
            return {"status": "blocked", "reason": "snapshot_not_fresh", "resource_count": 0, "document_count": 0}
        runtime_snapshot = snapshot_with_resolved_search_roots(self.project_root, snapshot or load_snapshot(self.project_root, self.core), self.workplace_root, self.core)
        index = ResourceSearchIndex(self.project_root, runtime_snapshot, self.workplace_root)
        try:
            before = index.status(verify_files=True)
            if before.get("status") in {"missing", "stale"}:
                after = index.maintenance_tick().get("after", {})
            else:
                after = before
        except LocalSearchError as exc:
            return {"status": "blocked", "reason": exc.code, "resource_count": 0, "document_count": 0}
        status = str(after.get("status") or "blocked")
        resource_count = int(after.get("resource_count") or 0)
        document_count = int(after.get("document_count") or 0)
        if status == "fresh" and document_count == 0:
            return {"status": "empty", "reason": "empty_corpus", "resource_count": resource_count, "document_count": document_count, "remediation": "Select or authorize searchable project resources."}
        if status == "fresh":
            return {"status": "ready", "reason": "fresh_index", "resource_count": resource_count, "document_count": document_count, "remediation": "none"}
        return {"status": "stale" if status == "stale" else "blocked", "reason": str(after.get("error") or status), "resource_count": resource_count, "document_count": document_count, "remediation": "Run safe technical search maintenance or refresh project context when required."}

    def search(self, *, query: Any, limit: Any = None, limitstart: Any = None, offset: Any = None) -> dict[str, Any]:
        check = self.core.project_context_check_result(self.project_root, explicit_workplace=str(self.workplace_root))
        if str(check.get("status") or "") not in {"fresh", "fresh_with_updates"}:
            raise LocalSearchError("snapshot_not_fresh")
        runtime_snapshot = snapshot_with_resolved_search_roots(self.project_root, load_snapshot(self.project_root, self.core), self.workplace_root, self.core)
        index = ResourceSearchIndex(self.project_root, runtime_snapshot, self.workplace_root)
        state = index.status(verify_files=True)
        if state.get("status") in {"missing", "stale"}:
            state = index.maintenance_tick().get("after", {})
        readiness = self.readiness(snapshot=runtime_snapshot, check=check)
        if readiness.get("status") == "empty":
            payload = index.search(query=query, limit=limit, limitstart=limitstart, offset=offset)
        else:
            payload = index.search(query=query, limit=limit, limitstart=limitstart, offset=offset)
        payload["garage_readiness"] = readiness
        payload["search"] = readiness
        add_private_navigation(payload, runtime_snapshot)
        return payload


@dataclass(frozen=True)
class ResourceResolveService:
    project_root: Path
    workplace_root: Path
    core: Any

    def resolve(self, *, resource_id: str | None = None) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema_version": 1,
            "kind": "pf.resolve",
            "project": {"id": self.core.project_id(self.project_root), "root": str(self.project_root)},
        }
        if not resource_id:
            return payload
        snapshot = load_snapshot(self.project_root, self.core)
        selected = selected_resource(snapshot, resource_id)
        if not selected:
            return {**payload, "resource": {"id": resource_id, "status": "denied", "reason": "not_in_project_snapshot"}}
        resource = {
            "id": resource_id,
            "status": "available",
            "scope": "project_context",
            "registry_source": "project-context.snapshot",
            "reference": selected.get("path_ref") or selected.get("path") or "",
            "application": selected.get("application") or {"package_id": selected.get("package_id"), "kind": selected.get("kind")},
        }
        if isinstance(selected.get("path_ref"), dict):
            resolution = resolve_garage_path_ref(self.project_root, selected["path_ref"], self.workplace_root, self.core)
            if resolution.get("status") == "resolved" and resolution.get("path"):
                resource["local_root"] = str(Path(str(resolution["path"])).resolve())
                resource["navigation"] = "private_runtime_authorized"
            else:
                resource["resolution_status"] = resolution.get("status") or "unresolved"
        return {**payload, "resource": resource}


@dataclass(frozen=True)
class ContextReconciliationService:
    project_root: Path
    workplace_root: Path
    core: Any

    def status(self) -> dict[str, Any]:
        check = self.core.project_context_check_result(self.project_root, explicit_workplace=str(self.workplace_root))
        stale_reasons = [str(item.get("reason") or "") for item in check.get("stale_resources", []) if isinstance(item, dict)]
        technical_only = bool(stale_reasons) and all(reason in {"valid_until expired"} or reason.startswith("source changed:") for reason in stale_reasons)
        return {
            "status": check.get("status"),
            "safe_automatic_refresh": bool(check.get("stale")) and technical_only,
            "operator_decision_required": bool(check.get("broken")) or (bool(check.get("stale")) and not technical_only),
            "reasons": stale_reasons,
        }


@dataclass(frozen=True)
class GovernedWorkBootstrapService:
    project_root: Path
    workplace_root: Path
    core: Any

    def guidance(self, *, objective: str = "") -> dict[str, Any]:
        summary = CurrentWorkService(self.project_root, self.core).summary()
        return {
            "schema_version": 1,
            "kind": "pf.work.start.guidance",
            "objective": objective,
            "work": summary,
            "recommendation": "continue_governed_work" if summary.get("governed") else "start_work",
        }

    def start(self, *, objective: str, preferred_stage: str = "", session_id: str = "") -> dict[str, Any]:
        # preferred_stage is retained only as a compatibility-only advanced
        # override. The public MCP schema no longer advertises it.
        return ProcessExecutionService(self.project_root, self.workplace_root, self.core).start(
            objective=objective,
            session_id=session_id,
            stage_override=str(preferred_stage or "").strip(),
        )


@dataclass(frozen=True)
class CurrentWorkService:
    project_root: Path
    core: Any

    def summary(self) -> dict[str, Any]:
        active = self.active_items()
        return {
            "governed": bool(active),
            "active_runs": compact_active_runs(active),
            "active_work": active[:10],
            "recommendation": "continue" if active else "start_work",
        }

    def active_items(self) -> list[dict[str, Any]]:
        return [item for item in self.items() if item["state"] == "active" and not item["bootstrap_placeholder"]]

    def find_by_objective(self, objective: str) -> dict[str, Any]:
        normalized = normalize_objective(objective)
        active: list[dict[str, Any]] = []
        historical: list[dict[str, Any]] = []
        for item in self.items():
            if item["bootstrap_placeholder"] or normalize_objective(str(item.get("objective") or "")) != normalized:
                continue
            if item["state"] == "active":
                active.append(item)
            elif item["state"] == "historical":
                historical.append(item)
        return {"active": active[0] if active else None, "historical": historical}

    def items(self) -> list[dict[str, Any]]:
        flow_root = self.core.locate_flow_root(self.project_root)
        rows: list[dict[str, Any]] = []
        runs_dir = flow_root / "runs"
        for run_path in sorted(runs_dir.glob("*/run.yaml")) if runs_dir.is_dir() else []:
            run = self.core.load_yaml_document(run_path)
            run_status = str(run.get("status") or "")
            run_id = str(run.get("id") or run_path.parent.name)
            tasks = run.get("tasks") if isinstance(run.get("tasks"), list) else []
            if not tasks:
                rows.append(work_item(run_id=run_id, run_status=run_status, task={}, run=run))
            for entry in tasks:
                if not isinstance(entry, dict):
                    continue
                task_id = str(entry.get("id") or "")
                task_path = flow_root / "assignments" / f"{task_id}.yaml"
                task = self.core.load_yaml_document(task_path) if task_path.is_file() else {"id": task_id, "status": entry.get("status"), "objective": run.get("objective")}
                rows.append(work_item(run_id=run_id, run_status=run_status, task=task, run=run))
        first = flow_root / "assignments" / "first-assignment.yaml"
        if first.is_file():
            task = self.core.load_yaml_document(first)
            rows.append(work_item(run_id="", run_status="", task=task, run={}))
        return rows


@dataclass(frozen=True)
class DerivedReportLifecycleService:
    project_root: Path
    core: Any

    def status(self, *, snapshot: dict[str, Any] | None = None) -> dict[str, Any]:
        snapshot = snapshot or load_snapshot(self.project_root, self.core)
        snapshot_time = str((snapshot.get("snapshot") if isinstance(snapshot.get("snapshot"), dict) else {}).get("generated_at") or snapshot.get("generated_at") or "")
        flow_root = self.core.locate_flow_root(self.project_root)
        reports = []
        for rel_path in DERIVED_REPORTS:
            path = flow_root / rel_path
            status = "missing"
            if path.is_file():
                status = "current"
                if snapshot_time:
                    try:
                        import datetime as _dt

                        generated = _dt.datetime.fromisoformat(snapshot_time.replace("Z", "+00:00")).timestamp()
                        if path.stat().st_mtime < generated:
                            status = "stale"
                    except (OSError, ValueError):
                        status = "historical"
            reports.append({"path": f".pf/{rel_path.as_posix()}", "status": status})
        aggregate = "stale" if any(item["status"] == "stale" for item in reports) else ("missing" if any(item["status"] == "missing" for item in reports) else "current")
        return {"status": aggregate, "snapshot_generated_at": snapshot_time, "reports": reports}


def load_snapshot(project_root: Path, core: Any) -> dict[str, Any]:
    snapshot_path, _snapshot_md = core.project_context_snapshot_paths(project_root)
    return core.load_yaml_document(snapshot_path)


def snapshot_with_resolved_search_roots(project_root: Path, snapshot: dict[str, Any], workplace_root: Path, core: Any) -> dict[str, Any]:
    runtime_snapshot = copy.deepcopy(snapshot)
    resources = runtime_snapshot.get("local_search_resources") if isinstance(runtime_snapshot.get("local_search_resources"), list) else []
    for resource in resources:
        if not isinstance(resource, dict) or not isinstance(resource.get("path_ref"), dict):
            continue
        resolution = resolve_garage_path_ref(project_root, resource["path_ref"], workplace_root, core)
        if resolution.get("status") == "resolved" and resolution.get("path"):
            resource["content_roots"] = [str(resolution["path"])]
    return runtime_snapshot


def resolve_garage_path_ref(project_root: Path, path_ref: dict[str, Any], workplace_root: Path, core: Any) -> dict[str, Any]:
    resolution = core.resolve_workspace_path_ref(project_root, path_ref, workplace_manifest=workplace_root / "workplace.yaml")
    if resolution.get("status") == "resolved":
        return resolution
    package_id = str(path_ref.get("package") or "")
    relative_path = str(path_ref.get("relative_path") or "").strip()
    if not package_id.startswith("project."):
        return resolution
    base = core.locate_flow_root(project_root)
    candidate = (base / relative_path).resolve() if relative_path else base.resolve()
    try:
        candidate.relative_to(base.resolve())
    except ValueError:
        return {"status": "unresolved", "reason": "invalid_path_ref: relative_path escapes project flow root"}
    return {"status": "resolved" if candidate.exists() else "missing", "path": str(candidate)}


def selected_resource(snapshot: dict[str, Any], resource_id: str) -> dict[str, Any]:
    candidates: list[Any] = []
    resolved = snapshot.get("resolved") if isinstance(snapshot.get("resolved"), dict) else {}
    for key in ("knowledge_resources",):
        if isinstance(resolved.get(key), list):
            candidates.extend(resolved[key])
    if isinstance(snapshot.get("local_search_resources"), list):
        candidates.extend(snapshot["local_search_resources"])
    for item in candidates:
        if not isinstance(item, dict):
            continue
        ids = {str(item.get("id") or ""), str(item.get("resource_id") or ""), str(item.get("instance_id") or "")}
        if resource_id in ids:
            return item
    return {}


def resource_selection_summary(snapshot: dict[str, Any]) -> dict[str, Any]:
    selection = snapshot.get("resource_selection") if isinstance(snapshot.get("resource_selection"), dict) else {}
    resolved = snapshot.get("resolved") if isinstance(snapshot.get("resolved"), dict) else {}
    selected = resolved.get("knowledge_resources") if isinstance(resolved.get("knowledge_resources"), list) else []
    preferred = [
        {
            "id": str(item.get("id") or ""),
            "kind": str(item.get("kind") or ""),
            "version": str(item.get("resolved_version") or item.get("resolved_generation") or ""),
            "reason": str((item.get("selection") or {}).get("reason") or ""),
        }
        for item in selected
        if isinstance(item, dict)
    ]
    return {
        "mode": str(selection.get("mode") or "snapshot"),
        "available_count": int(selection.get("available_count") or len(resolved.get("available_knowledge_resources") or [])),
        "selected_count": int(selection.get("selected_count") or len(preferred)),
        "target_versions": selection.get("target_versions") if isinstance(selection.get("target_versions"), list) else [],
        "preferred": preferred,
    }


def add_private_navigation(payload: dict[str, Any], runtime_snapshot: dict[str, Any]) -> None:
    resources = runtime_snapshot.get("local_search_resources") if isinstance(runtime_snapshot.get("local_search_resources"), list) else []
    by_id = {str(item.get("id") or item.get("resource_id") or ""): item for item in resources if isinstance(item, dict)}
    for match in payload.get("results", []):
        if not isinstance(match, dict):
            continue
        resource = by_id.get(str(match.get("resource_id") or ""))
        roots = resource.get("content_roots") if isinstance(resource, dict) and isinstance(resource.get("content_roots"), list) else []
        for raw_root in roots:
            root = Path(str(raw_root)).resolve()
            candidate = (root / str(match.get("canonical_path") or "")).resolve() if root.is_dir() else root
            try:
                candidate.relative_to(root if root.is_dir() else candidate)
            except ValueError:
                continue
            if candidate.is_file():
                match["local_path"] = str(candidate)
                match["navigation"] = "private_runtime_authorized"
                break


def process_summary(snapshot: dict[str, Any]) -> dict[str, Any]:
    processes = snapshot.get("processes") if isinstance(snapshot.get("processes"), dict) else {}
    current = processes.get("current") if isinstance(processes.get("current"), dict) else {}
    return {"id": str(current.get("id") or ""), "stage_count": len(current.get("stages") or []) if isinstance(current.get("stages"), list) else 0}


def governed_work_summary(project_root: Path, core: Any) -> dict[str, Any]:
    return CurrentWorkService(project_root, core).summary()


def diagnostics_from_check(check: dict[str, Any], search: dict[str, Any], mode: dict[str, Any] | None = None) -> list[dict[str, str]]:
    diagnostics: list[dict[str, str]] = []
    if check.get("status") not in {"fresh", "fresh_with_updates"}:
        diagnostics.append({"code": "context_not_fresh", "severity": "blocked", "message": str(check.get("recommended_action") or "refresh required")})
    if search.get("status") == "empty":
        diagnostics.append({"code": "search_corpus_empty", "severity": "warn", "message": "No authorized searchable documents are indexed."})
    elif search.get("status") in {"stale", "blocked"}:
        diagnostics.append({"code": str(search.get("reason") or "search_not_ready"), "severity": "blocked", "message": "Search is not ready."})
    for blocker in (mode or {}).get("blockers", []):
        if isinstance(blocker, dict):
            diagnostics.append({"code": str(blocker.get("code") or "mode_blocker"), "severity": "blocked", "message": str(blocker.get("message") or "")})
    return diagnostics


ACTIVE_STATUSES = {"open", "in_progress", "review", "blocked"}
HISTORICAL_STATUSES = {"done", "completed", "cancelled", "failed"}
DERIVED_REPORTS = [
    Path("artifacts/project-classification-report.md"),
    Path("artifacts/global-resource-matching-report.md"),
    Path("artifacts/toolchain-detection-report.md"),
    Path("artifacts/capability-provider-audit.md"),
    Path("artifacts/project-profile.md"),
]


def selected_process_id(project_root: Path, core: Any) -> str:
    manifest = core.load_yaml_document(core.locate_flow_root(project_root) / "process-forge.yaml")
    process_id = str(manifest.get("process") or "").strip()
    return process_id or "task-batch-execution"


def resolve_process(project_root: Path, process_id: str, core: Any) -> dict[str, Any]:
    try:
        definition = core.resolve_process_definition(project_root, process_id)
        return definition.process
    except Exception:
        return {"id": process_id, "stages": []}


def valid_stages(process: dict[str, Any]) -> list[str]:
    return [str(item.get("id") or "") for item in process.get("stages", []) if isinstance(item, dict) and str(item.get("id") or "")]


def stage_obligations(process: dict[str, Any], stage_id: str) -> list[dict[str, Any]]:
    for stage in process.get("stages", []) if isinstance(process.get("stages"), list) else []:
        if isinstance(stage, dict) and str(stage.get("id") or "") == stage_id:
            return stage.get("automation_bindings") if isinstance(stage.get("automation_bindings"), list) else []
    return []


def unique_id(root: Path, seed: str) -> str:
    base = "-".join(str(seed or "work").lower().split())[:72].strip("-") or "work"
    candidate = base
    index = 2
    while (root / candidate).exists() or (root / f"{candidate}.yaml").exists():
        suffix = f"-{index}"
        candidate = base[: 72 - len(suffix)] + suffix
        index += 1
    return candidate


def normalize_objective(value: str) -> str:
    return " ".join(value.casefold().split())


def work_item(*, run_id: str, run_status: str, task: dict[str, Any], run: dict[str, Any]) -> dict[str, Any]:
    task_id = str(task.get("id") or "")
    task_status = str(task.get("status") or run_status or "")
    state = "active" if task_status in ACTIVE_STATUSES or run_status in ACTIVE_STATUSES else ("historical" if task_status in HISTORICAL_STATUSES or run_status in HISTORICAL_STATUSES else "other")
    bootstrap = task_id == "first-assignment" or str(task.get("objective") or "").lower().startswith("verify processforge project onboarding")
    return {
        "run_id": run_id,
        "assignment_id": task_id,
        "run_status": run_status,
        "status": task_status,
        "state": state,
        "stage": str(task.get("stage") or ""),
        "process": str(task.get("process") or run.get("process") or ""),
        "objective": str(task.get("objective") or run.get("objective") or ""),
        "bootstrap_placeholder": bootstrap,
    }


def compact_active_runs(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    result: list[dict[str, Any]] = []
    for item in items:
        run_id = str(item.get("run_id") or "")
        if not run_id or run_id in seen:
            continue
        seen.add(run_id)
        result.append({"run_id": run_id, "status": item.get("run_status"), "process": item.get("process")})
    return result[:10]
