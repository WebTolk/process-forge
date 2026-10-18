"""Existing guidance and governed Work start delegation."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Protocol


class WorkStart(Protocol):
    def __call__(self, *, objective: str, process_id: str = "", session_id: str = "", stage_override: str = "") -> dict[str, Any]: ...


@dataclass(frozen=True)
class GovernedWorkBootstrapService:
    current_work_summary: Callable[[], dict[str, Any]] = field(kw_only=True, repr=False, compare=False)
    work_start: Callable[[], WorkStart] = field(kw_only=True, repr=False, compare=False)

    def guidance(self, *, objective: str = "") -> dict[str, Any]:
        summary = self.current_work_summary()
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
        return self.work_start()(
            objective=objective,
            process_id=str(process_id or "").strip(),
            session_id=session_id,
            stage_override=str(preferred_stage or "").strip(),
        )
