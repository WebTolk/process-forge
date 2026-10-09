"""Garage-level project context, search, and resolve services."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .ports import ProjectSnapshotReadPort, WorkReadCorePort
from .process_execution import ProcessExecutionService
from .common.request_scope import scoped_request
from .work.inventory import WorkInventory
from .resources.access import ResourceSearchService
from .project.snapshot import load_snapshot
from .resources.snapshot import resource_selection_summary, snapshot_with_resolved_search_roots


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
