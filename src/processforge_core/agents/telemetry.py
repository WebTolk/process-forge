"""Telemetry redaction, append operations and event envelopes."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any
import uuid

from ..common.clock import now_utc
from ..common.privacy import contains_secret_value
from ..project.metadata import PROJECT_FLOW_ROOT
from ..work.context_documents import ContextContractInputs


class TelemetryEventService:
    """Own the existing telemetry algorithms with concrete project inputs."""

    def __init__(self, context_inputs: ContextContractInputs | None = None) -> None:
        self.context_inputs = context_inputs if context_inputs is not None else ContextContractInputs()

    def telemetry_session_id(self, prefix: str = "session") -> str:
        stamp = now_utc().replace("-", "").replace(":", "").replace("Z", "z")
        return f"{prefix}-{stamp}"

    def redact_telemetry_value(self, value: Any) -> Any:
        if isinstance(value, dict):
            return {key: self.redact_telemetry_value(item) for key, item in value.items()}
        if isinstance(value, list):
            return [self.redact_telemetry_value(item) for item in value]
        if isinstance(value, str) and contains_secret_value(value):
            return "<redacted>"
        return value

    def append_telemetry_event(self, telemetry_path: Path, event: str, **payload: Any) -> None:
        telemetry_path.parent.mkdir(parents=True, exist_ok=True)
        item = {"ts": now_utc(), "event": event}
        item.update(self.redact_telemetry_value(payload))
        with telemetry_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(item, ensure_ascii=False, sort_keys=True) + "\n")

    def flow_label(self, project_root: Path) -> str:
        return PROJECT_FLOW_ROOT

    def processforge_event(
        self,
        project_root: Path,
        event_type: str,
        *,
        severity: str = "info",
        session_id: str | None = None,
        assignment_id_value: str | None = None,
        assignment_path: str | None = None,
        process_id: str | None = None,
        process_version: str | None = None,
        stage: str | None = None,
        subject: str | None = None,
        payload: dict[str, Any] | None = None,
        data: dict[str, Any] | None = None,
        privacy: str = "private",
        correlation_id: str | None = None,
        causation_id: str | None = None,
        event_id: str | None = None,
        actor: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        correlation = correlation_id or session_id or f"corr-{uuid.uuid4().hex[:12]}"
        event_id = event_id or f"evt_{uuid.uuid4().hex}"
        clean_data = self.redact_telemetry_value(data if data is not None else (payload or {}))
        actor_data = actor or {"type": "agent", "id": "processforge-cli", "role": "orchestrator"}
        event_subject = subject or assignment_path or assignment_id_value or session_id or event_type
        return {
            "schema_version": 1,
            "event_id": event_id,
            "event_type": event_type,
            "source": "processforge.cli",
            "subject": event_subject,
            "time": now_utc(),
            "correlation_id": correlation,
            "causation_id": causation_id,
            "project": {"flow_root": self.flow_label(project_root), "project_id": self.context_inputs.project_id(project_root)},
            "process": {"id": process_id, "version": process_version, "stage_id": stage, "process_run_id": None},
            "assignment": {"id": assignment_id_value, "path": assignment_path},
            "actor": actor_data,
            "session": {"id": session_id},
            "data": clean_data,
            "severity": severity,
            "privacy": privacy,
        }
