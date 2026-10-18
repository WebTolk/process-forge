from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from processforge_core.common.ids import opaque_identity_digest, safe_id
from processforge_core.common.ndjson import NdjsonReader


@dataclass(frozen=True)
class ChatTranscriptReader:
    """Own transcript paths and exact-session reads of current file records."""

    project_root: Path
    documents: NdjsonReader = field(default_factory=NdjsonReader)

    @property
    def directory(self) -> Path:
        return self.project_root / ".pf" / "runtime" / "chat" / "transcripts"

    def path(self, session_id: str) -> Path:
        return self.directory / f"session-{opaque_identity_digest(session_id)}.ndjson"

    def legacy_path(self, session_id: str) -> Path:
        return self.directory / f"{safe_id(session_id, 'session')}.ndjson"

    def messages(self, session_id: str) -> list[dict[str, Any]]:
        transcript = self.path(session_id)
        messages: list[dict[str, Any]] = []
        seen: set[str] = set()
        for path in (self.legacy_path(session_id), transcript):
            for _line_number, data, error in self.documents.read(path):
                if error is None and isinstance(data, dict) and data.get("session_id") == session_id:
                    message_id = str(data.get("message_id") or "")
                    if message_id and message_id in seen:
                        continue
                    if message_id:
                        seen.add(message_id)
                    messages.append(data)
        return messages
