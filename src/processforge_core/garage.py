"""Garage-level project context, search, and resolve services."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .ports import ProjectSnapshotReadPort, WorkReadCorePort
from .process_execution import ProcessExecutionService, project_process_selection
from .common.request_scope import scoped_request
from .work.inventory import WorkInventory
from .resources.access import ResourceSearchService
from .project.snapshot import load_snapshot
from .resources.snapshot import resource_selection_summary, snapshot_with_resolved_search_roots


@dataclass(frozen=True)
class ProjectContextService:
    project_root: Path
    workplace_root: Path
    core: Any
    snapshots: ProjectSnapshotReadPort | None = field(default=None, kw_only=True, repr=False, compare=False)

    def project_id(self) -> str:
        return str(self.core.project_id(self.project_root))

    def snapshot(self) -> dict[str, Any]:
        return load_snapshot(self.project_root, self.core, snapshots=self.snapshots)

    def check(self) -> dict[str, Any]:
        return self.core.project_context_check_result(self.project_root, explicit_workplace=str(self.workplace_root))

    def runtime_snapshot(self) -> dict[str, Any]:
        return snapshot_with_resolved_search_roots(self.project_root, self.snapshot(), self.workplace_root, self.core)

    @scoped_request
    def context(self, *, session_id: str = "") -> dict[str, Any]:
        from .composition import build_garage_mode_service

        check = self.check()
        snapshot = self.snapshot() if not check.get("broken") else {}
        manifest = self.core.load_yaml_document(self.core.locate_flow_root(self.project_root) / "process-forge.yaml")
        search = ResourceSearchService(self.project_root, self.workplace_root, self.core).readiness(snapshot=snapshot, check=check)
        mode = build_garage_mode_service(self.project_root, self.workplace_root, self.core).status(snapshot=snapshot, session_id=session_id)
        work = CurrentWorkService(self.project_root, self.core).summary()
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
            "process": process_summary(snapshot, manifest, project_root=self.project_root, core=self.core),
            "resources": {
                "search_status": search.get("status"),
                "reason": search.get("reason"),
                "resource_count": search.get("resource_count"),
                "document_count": search.get("document_count"),
                "search": search,
                "selection": resource_selection_summary(snapshot),
            },
            "work": work,
            "derived_reports": DerivedReportLifecycleService(self.project_root, self.core).status(snapshot=snapshot),
            "session": mode["session"],
            "diagnostics": diagnostics_from_check(check, search, mode),
        }
        continuation = fresh_session_continuation(self.project_root, self.core, work)
        if continuation:
            payload["work"]["recommendation"] = "continue_from_handoff"
            payload["continuation"] = continuation
        return payload


@dataclass(frozen=True)
class GarageModeService:
    project_root: Path
    workplace_root: Path
    core: Any
    snapshots: ProjectSnapshotReadPort | None = field(default=None, kw_only=True, repr=False, compare=False)

    def status(self, *, snapshot: dict[str, Any] | None = None, session_id: str = "") -> dict[str, Any]:
        snapshot = snapshot or load_snapshot(self.project_root, self.core, snapshots=self.snapshots)
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

    def start(self, *, objective: str, process_id: str = "", preferred_stage: str = "", session_id: str = "") -> dict[str, Any]:
        # preferred_stage is retained only as a compatibility-only advanced
        # override. The public MCP schema no longer advertises it.
        return ProcessExecutionService(self.project_root, self.workplace_root, self.core).start(
            objective=objective,
            process_id=str(process_id or "").strip(),
            session_id=session_id,
            stage_override=str(preferred_stage or "").strip(),
        )


@dataclass(frozen=True)
class CurrentWorkService:
    project_root: Path
    core: WorkReadCorePort

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
        inventory = WorkInventory(flow_root, self.core.load_yaml_document)
        rows: list[dict[str, Any]] = []
        for run_path, run in inventory.runs():
            run_status = str(run.get("status") or "")
            run_id = str(run.get("id") or run_path.parent.name)
            tasks = run.get("tasks") if isinstance(run.get("tasks"), list) else []
            if not tasks:
                rows.append(work_item(run_id=run_id, run_status=run_status, task={}, run=run))
            for entry in tasks:
                if not isinstance(entry, dict):
                    continue
                task_id = str(entry.get("id") or "")
                task_path = inventory.assignment_path(task_id)
                task = inventory.assignment(task_id) if task_path.is_file() else {"id": task_id, "status": entry.get("status"), "objective": run.get("objective")}
                rows.append(work_item(run_id=run_id, run_status=run_status, task=task, run=run))
        first = inventory.assignment_path("first-assignment")
        if first.is_file():
            task = inventory.assignment("first-assignment")
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


def process_summary(snapshot: dict[str, Any], manifest: dict[str, Any] | None = None, *, project_root: Path | None = None, core: Any = None) -> dict[str, Any]:
    processes = snapshot.get("processes") if isinstance(snapshot.get("processes"), dict) else {}
    current = processes.get("current") if isinstance(processes.get("current"), dict) else {}
    selection = processes.get("selection") if isinstance(processes.get("selection"), dict) else project_process_selection(manifest or {})
    allowed = selection.get("allowed") if isinstance(selection.get("allowed"), list) else []
    candidates = []
    for process_id in allowed:
        item = {"id": str(process_id), "title": str(process_id), "purpose": ""}
        if project_root is not None and core is not None:
            try:
                process = core.resolve_process_definition(project_root, str(process_id)).process
                item["title"] = str(process.get("name") or process_id)
                item["purpose"] = str(process.get("purpose") or process.get("description") or "")
            except (OSError, ValueError, SystemExit):
                pass
        candidates.append(item)
    return {
        "id": str(current.get("id") or ""),
        "stage_count": len(current.get("stages") or []) if isinstance(current.get("stages"), list) else 0,
        "default": str(selection.get("default") or ""),
        "allowed": candidates,
    }


def fresh_session_continuation(project_root: Path, core: Any, work: dict[str, Any]) -> dict[str, Any]:
    """Return the newest usable completed Work boundary, never an older one."""
    if work.get("governed"):
        return {}
    flow_root = core.locate_flow_root(project_root)
    candidates: list[tuple[str, dict[str, Any], Path]] = []
    for run_path in (flow_root / "runs").glob("*/run.yaml"):
        run = core.load_yaml_document(run_path)
        if str(run.get("status") or "") != "completed":
            continue
        artifacts = run.get("final_artifacts") if isinstance(run.get("final_artifacts"), list) else []
        handoff = next((str(item) for item in artifacts if str(item).endswith("-handoff.md")), "")
        if not handoff or not (project_root / handoff).is_file():
            continue
        candidates.append((str(run.get("updated_at") or run.get("created_at") or ""), run, project_root / handoff))
    if not candidates:
        return {}
    _timestamp, run, handoff_path = max(candidates, key=lambda item: item[0])
    pin = run.get("process_execution") if isinstance(run.get("process_execution"), dict) else {}
    previous_process = str(run.get("process") or "")
    allowed_processes = pin.get("allowed_processes") if isinstance(pin.get("allowed_processes"), list) else []
    available = []
    for value in allowed_processes:
        process_id = str(value or "").strip()
        if process_id and process_id != previous_process and process_id not in available:
            available.append(process_id)
    definition = pin.get("definition") if isinstance(pin.get("definition"), dict) else {}
    routed = [str(item.get("to_process") or item.get("target_process") or "") for item in definition.get("process_transitions", []) if isinstance(item, dict)]
    routes_path = flow_root / "process-routes.yaml"
    if routes_path.is_file():
        routes = core.load_yaml_document(routes_path).get("routes", [])
        routed.extend(str(item.get("to_process") or item.get("target_process") or "") for item in routes if isinstance(item, dict) and str(item.get("from_process") or "") == previous_process)
    recommended = next((item for item in routed if item in available), "")
    # The newest completed boundary is authoritative. If it has no route, do
    # not resurrect an older handoff merely because that one had a suggestion.
    if not recommended:
        return {}
    summary = next((str(item) for item in run.get("final_artifacts", []) if str(item).endswith("summary.md")), "")
    return {
        "previous_run_id": str(run.get("id") or ""),
        "previous_process_id": previous_process,
        "handoff_path": core.rel(handoff_path, project_root),
        "summary_path": summary,
        "next": {"recommended_process": recommended, "available_processes": available},
        "session_continuity": {"recommendation": "fresh", "reason": "process_boundary"},
    }


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
