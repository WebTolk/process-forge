"""CLI adapter for Work operations owned by a running Forge Runtime."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Self


class ForgeWorkError(Exception):
    """A selected Forge Runtime could not complete the native CLI operation."""


class ForgeWorkClient:
    def __init__(self, project: Path, workplace: Path) -> None:
        self._project = project
        self._workplace = workplace

    @classmethod
    def select(cls, project: Path, manifest: Path | None) -> Self | None:
        if manifest is None:
            return None
        from pf_runtime.mcp_bridge import BackendUnavailable, forge_workplace

        try:
            if forge_workplace(str(manifest.parent)):
                return cls(project, manifest.parent)
        except (BackendUnavailable, OSError, ValueError) as exc:
            raise ForgeWorkError("forge_workplace_unavailable") from exc
        return None

    def _call(self, name: str, values: dict[str, Any]) -> dict[str, Any]:
        from http.client import HTTPException

        from pf_runtime.mcp_bridge import (
            BackendUnavailable,
            runtime_tool_result,
            runtime_work_start,
        )

        arguments = {
            key: value
            for key, value in values.items()
            if value is not None and (value != "" or key == "objective")
        }
        arguments["project_root"] = str(self._project)
        try:
            if name == "pf.work.start":
                return runtime_work_start(self._workplace, arguments)
            result = runtime_tool_result(self._workplace, name, arguments)
        except (BackendUnavailable, HTTPException, OSError, ValueError) as exc:
            raise ForgeWorkError("forge_runtime_unavailable") from exc
        error = result.get("error")
        if isinstance(error, dict):
            raise ForgeWorkError(str(error.get("code") or "forge_operation_failed"))
        return result

    def start(
        self,
        *,
        objective: str,
        process_id: str,
        security: dict[str, Any] | None,
        scope_intent: dict[str, Any] | None,
    ) -> dict[str, Any]:
        return self._call(
            "pf.work.start",
            {
                "objective": objective,
                "process_id": process_id,
                "security": security,
                "scope_intent": scope_intent,
            },
        )

    def state(
        self,
        *,
        run_id: str,
        assignment_id: str,
        context_id: str,
        session_id: str,
    ) -> dict[str, Any]:
        return self._call(
            "pf.work.state",
            {
                "run_id": run_id,
                "assignment_id": assignment_id,
                "context_id": context_id,
                "session_id": session_id,
            },
        )

    def transition(
        self,
        *,
        outcome: str,
        evidence: list[Any],
        notes: str,
        run_id: str,
        assignment_id: str,
        context_id: str,
        session_id: str,
    ) -> dict[str, Any]:
        return self._call(
            "pf.work.transition",
            {
                "outcome": outcome,
                "evidence": evidence,
                "notes": notes,
                "run_id": run_id,
                "assignment_id": assignment_id,
                "context_id": context_id,
                "session_id": session_id,
            },
        )

    def read(self, *, operation: str, **values: Any) -> dict[str, Any]:
        if operation == "search":
            return self._call("pf.work.search", values)
        if operation == "resolve":
            return self._call("pf.work.resolve", values)
        raise ValueError("unknown Work resource operation")

    def continuation(self, operation: str, **values: Any) -> dict[str, Any]:
        names = {
            "create": "pf.continuation.create",
            "status": "pf.continuation.status",
            "resume": "pf.continuation.resume",
            "cancel_work": "pf.work.cancel",
        }
        return self._call(names[operation], values)
