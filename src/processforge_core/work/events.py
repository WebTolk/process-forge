"""Existing Work event publication through a deferred typed emitter."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol


class ProcessEventEmitter(Protocol):
    def __call__(
        self,
        project_root: Path,
        event_type: str,
        *,
        process_id: str,
        process_version: str,
        stage: str,
        subject: str,
        assignment_id_value: str,
        assignment_path: str | None,
        payload: dict[str, Any],
        correlation_id: str,
        event_id: str | None,
    ) -> dict[str, Any]: ...


@dataclass(frozen=True, kw_only=True)
class WorkEventPublisher:
    project_root: Path
    has_emitter: Callable[[], bool] = field(repr=False, compare=False)
    emitter: Callable[[], ProcessEventEmitter] = field(repr=False, compare=False)

    def publish(self, event_type: str, run: dict[str, Any], assignment: dict[str, Any], stage_id: str, *, outcome: str, previous_stage_id: str = "", next_stage_id: str = "", blockers: list[dict[str, Any]] | None = None, event_id: str | None = None) -> None:
        if not self.has_emitter():
            return
        self.emitter()(
            self.project_root,
            event_type,
            process_id=str(run.get("process") or ""),
            process_version=str((run.get("process_execution") or {}).get("process_version") or ""),
            stage=stage_id,
            subject=str(assignment.get("id") or run.get("id") or event_type),
            assignment_id_value=str(assignment.get("id") or ""),
            assignment_path=f".pf/assignments/{assignment.get('id')}.yaml" if assignment.get("id") else None,
            payload={
                "run_id": str(run.get("id") or ""),
                "assignment_id": str(assignment.get("id") or ""),
                "process_id": str(run.get("process") or ""),
                "stage_id": stage_id,
                "previous_stage_id": previous_stage_id,
                "next_stage_id": next_stage_id,
                "outcome": outcome,
                "blockers": blockers or [],
            },
            correlation_id=f"run-{run.get('id')}",
            event_id=event_id,
        )
        from .. import diagnostics
        diagnostics.select_work(self.project_root, str(run.get("id") or ""), assignment.get("id"))
        diagnostics.annotate(run_id=run.get("id"), assignment_id=assignment.get("id"), stage_id=stage_id)
        diagnostics.emit("warning" if blockers else "info", "work.event_recorded", {
            "event_type": event_type, "outcome": outcome, "blockers": blockers or [],
        }, component="work")
