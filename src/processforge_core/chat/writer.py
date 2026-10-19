"""Append existing chat records under their transcript lock and emit events."""

from __future__ import annotations

import json
import os
import time
import uuid
from pathlib import Path
from typing import Any

import processforge_core.common.clock as _core_common_clock

from ..agents.process_events import ProcessEventRecorder
from ..common.ids import opaque_identity_digest
from ..common.ndjson import NdjsonReader
from ..common.paths import rel
from .export import ChatExportService
from .transcripts import ChatTranscriptReader


class ChatTranscriptWriter:
    def __init__(
        self,
        *,
        events: ProcessEventRecorder | None = None,
        exports: ChatExportService | None = None,
        documents: NdjsonReader | None = None,
    ) -> None:
        self.events = events if events is not None else ProcessEventRecorder()
        self.exports = exports if exports is not None else ChatExportService()
        self.documents = documents if documents is not None else NdjsonReader()

    def append_chat_message(
        self,
        project_root: Path,
        *,
        session_id: str,
        participant_id: str,
        participant_role: str,
        message_role: str,
        content: str,
        participant_type: str | None = None,
        turn_id: str | None = None,
        parent_message_id: str | None = None,
        source_kind: str = "manual_capture",
        process_id: str | None = None,
        stage_id: str | None = None,
        assignment_id_value: str | None = None,
        include_event_content: bool = False,
        message_id: str | None = None,
        event_id: str | None = None,
    ) -> tuple[Path, dict[str, Any], dict[str, Any]]:
        transcript = ChatTranscriptReader(project_root).path(session_id)
        transcript.parent.mkdir(parents=True, exist_ok=True)
        requested_message_id = message_id or f"msg_{uuid.uuid4().hex}"
        redacted_content, redaction = self.exports.redact_chat_content(content)
        lock = transcript.with_suffix(transcript.suffix + ".lock")
        deadline = time.monotonic() + 20.0
        descriptor: int | None = None
        while descriptor is None:
            try:
                descriptor = os.open(str(lock), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            except FileExistsError:
                if time.monotonic() >= deadline:
                    raise SystemExit(f"FAIL: timed out waiting for chat transcript lock: {lock.name}")
                time.sleep(0.05)
        try:
            existing_lines = transcript.read_text(encoding="utf-8", errors="replace").splitlines() if transcript.is_file() else []
            prior_records = [
                (path, data)
                for path in (transcript, ChatTranscriptReader(project_root).legacy_path(session_id))
                for _line, data, error in self.documents.read(path)
                if error is None and isinstance(data, dict) and data.get("session_id") == session_id
            ]
            for existing_path, existing in prior_records:
                if str(existing.get("message_id") or "") == requested_message_id:
                    if event_id:
                        body = existing.get("message") if isinstance(existing.get("message"), dict) else {}
                        existing_participant = existing.get("participant") if isinstance(existing.get("participant"), dict) else {}
                        core_data = {
                            "session_id": session_id,
                            "message_id": requested_message_id,
                            "participant": existing_participant,
                            "message": {
                                "role": body.get("role"),
                                "content_hash": body.get("content_hash"),
                                "redaction": body.get("redaction", "none"),
                                "content_ref": {"path": rel(existing_path, project_root), "line": 0, "message_id": requested_message_id},
                                "content_mode": "metadata_only",
                            },
                        }
                        self.events.emit_process_event(project_root, "chat.message.recorded", session_id=session_id, assignment_id_value=assignment_id_value, process_id=process_id, stage=stage_id, subject=f"chat/{session_id}/{requested_message_id}", data=core_data, privacy="private", correlation_id=session_id, event_id=event_id)
                    return existing_path, existing, {}
            line_number = len([line for line in existing_lines if line.strip()]) + 1
            record = {
            "schema_version": 1,
            "message_id": requested_message_id,
            "session_id": session_id,
            "turn_id": turn_id or f"turn_{len(prior_records) + 1}",
            "parent_message_id": parent_message_id,
            "timestamp": _core_common_clock.now_utc(),
            "participant": self.exports.chat_participant(participant_id, participant_role, participant_type),
            "message": {
                "role": message_role,
                "content_type": "text/markdown",
                "content": redacted_content,
                "content_hash": 'sha256:' + opaque_identity_digest(redacted_content),
                "redaction": redaction,
            },
            "source": {"kind": source_kind, "hook_event": None, "transcript_path": rel(transcript, project_root)},
            "process": {"id": process_id, "stage_id": stage_id},
            "assignment": {"id": assignment_id_value},
            }
            with transcript.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
            content_ref = {"path": rel(transcript, project_root), "line": line_number, "message_id": requested_message_id}
            event_data: dict[str, Any] = {
            "session_id": session_id,
            "message_id": requested_message_id,
            "participant": record["participant"],
            "message": {
                "role": message_role,
                "content_hash": record["message"]["content_hash"],
                "redaction": redaction,
                "content_ref": content_ref,
            },
            }
            if include_event_content:
                event_data["message"]["content"] = redacted_content
                event_data["message"]["content_mode"] = "full" if redaction == "none" else redaction
            else:
                event_data["message"]["content_mode"] = "metadata_only"
            event = self.events.emit_process_event(
            project_root,
            "chat.message.recorded",
            session_id=session_id,
            assignment_id_value=assignment_id_value,
            process_id=process_id,
            stage=stage_id,
            subject=f"chat/{session_id}/{requested_message_id}",
            data=event_data,
            privacy="private",
            correlation_id=session_id,
            event_id=event_id,
            )
            return transcript, record, event
        finally:
            if descriptor is not None:
                os.close(descriptor)
            lock.unlink(missing_ok=True)
