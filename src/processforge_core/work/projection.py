"""Existing I/O-free current Work projection and classification rules."""

from __future__ import annotations

from typing import Any

ACTIVE_STATUSES = {"open", "in_progress", "review", "blocked"}
HISTORICAL_STATUSES = {"done", "completed", "cancelled", "failed"}


class WorkProjectionPolicy:
    def normalize_objective(self, value: str) -> str:
        return " ".join(value.casefold().split())

    def work_item(self, *, run_id: str, run_status: str, task: dict[str, Any], run: dict[str, Any]) -> dict[str, Any]:
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

    def compact_active_runs(self, items: list[dict[str, Any]]) -> list[dict[str, Any]]:
        seen: set[str] = set()
        result: list[dict[str, Any]] = []
        for item in items:
            run_id = str(item.get("run_id") or "")
            if not run_id or run_id in seen:
                continue
            seen.add(run_id)
            result.append({"run_id": run_id, "status": item.get("run_status"), "process": item.get("process")})
        return result[:10]

