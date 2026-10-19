"""Workplace resource event journals: existing algorithms owned by Core."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
import uuid

from processforge_core.agents.telemetry import TelemetryEventService
from processforge_core.common.clock import now_utc
from processforge_core.common.ids import safe_id
from processforge_core.documents.reader import YamlDocumentReader


class WorkplaceResourceEventJournal:
    def __init__(self, documents: YamlDocumentReader, telemetry: TelemetryEventService) -> None:
        self._documents = documents
        self._telemetry = telemetry

    def workplace_event(self, root: Path, event_type: str, *, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        manifest = root / "workplace.yaml"
        workplace_id = safe_id(root.name or "workplace", "workplace")
        if manifest.is_file():
            data = self._documents.load(manifest)
            workplace = data.get("workplace") if isinstance(data, dict) else None
            if isinstance(workplace, dict) and workplace.get("id"):
                workplace_id = safe_id(str(workplace["id"]), "workplace")
        return {
            "schema_version": 1,
            "event_id": f"evt_{uuid.uuid4().hex}",
            "event_type": event_type,
            "source": "processforge.cli",
            "subject": workplace_id,
            "time": now_utc(),
            "correlation_id": f"workplace-init-{workplace_id}",
            "project": {"flow_root": "workplace", "project_id": workplace_id},
            "process": {"id": "workplace-initialization", "version": "1.0.0", "stage_id": None, "process_run_id": None},
            "assignment": {"id": None, "path": None},
            "actor": {"type": "agent", "id": "processforge-cli", "role": "orchestrator"},
            "session": {"id": None},
            "data": payload or {},
            "severity": "info",
            "privacy": "private",
        }

    def append_workplace_event(self, root: Path, event_type: str, *, payload: dict[str, Any] | None = None) -> Path:
        events_path = root / "runtime" / "events" / "events.ndjson"
        events_path.parent.mkdir(parents=True, exist_ok=True)
        with events_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(self.workplace_event(root, event_type, payload=payload), ensure_ascii=False, sort_keys=True) + "\n")
        return events_path

    def resource_management_event(
        self,
        *,
        scope: str,
        command: str,
        event_type: str,
        target: dict[str, Any],
        status: str,
        message: str,
        event_id: str | None = None,
    ) -> dict[str, Any]:
        return {
            "schema_version": 1,
            "event_id": event_id or f"evt_{uuid.uuid4().hex}",
            "event_type": event_type,
            "occurred_at": now_utc(),
            "scope": scope,
            "source": {"command": command, "actor_type": "agent"},
            "target": target,
            "result": {"status": status, "message": message},
        }

    def append_workplace_resource_event(self, workplace_root: Path, event: dict[str, Any]) -> Path:
        target = workplace_root / "runtime" / "events" / "events.ndjson"
        target.parent.mkdir(parents=True, exist_ok=True)
        event_id = str(event.get("event_id") or "")
        if event_id and target.is_file():
            for line in target.read_text(encoding="utf-8", errors="replace").splitlines():
                try:
                    existing = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if isinstance(existing, dict) and str(existing.get("event_id") or "") == event_id:
                    return target
        target.write_text(
            (target.read_text(encoding="utf-8") if target.is_file() else "")
            + json.dumps(self._telemetry.redact_telemetry_value(event), ensure_ascii=False, sort_keys=True)
            + "\n",
            encoding="utf-8",
        )
        self.mark_search_index_dirty_after_resource_event(workplace_root, event)
        return target

    def mark_search_index_dirty_after_resource_event(self, workplace_root: Path, event: dict[str, Any]) -> None:
        result = event.get("result") if isinstance(event.get("result"), dict) else {}
        status = str(result.get("status") or "")
        if status in {"dry_run", "skipped", "passed", "failed"}:
            return
        try:
            from processforge_core.resources.local_search import ResourceSearchIndex

            ResourceSearchIndex(workplace_root, workplace_root=workplace_root).mark_dirty(reason=str(event.get("event_type") or "resource_event"))
        except Exception:
            return
