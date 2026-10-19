"""Chat redaction, participant values and export projections."""
from __future__ import annotations

from typing import Any

from ..common.privacy import SECRET_VALUE_PATTERNS


class ChatExportService:
    """Own the existing chat projection algorithms."""

    def redact_chat_content(self, content: str, max_chars: int = 20000) -> tuple[str, str]:
        redacted = content
        redaction = "none"
        for pattern in SECRET_VALUE_PATTERNS:
            redacted, count = pattern.subn("<redacted>", redacted)
            if count:
                redaction = "redacted"
        if len(redacted) > max_chars:
            redacted = redacted[:max_chars]
            redaction = "truncated" if redaction == "none" else "redacted_truncated"
        return redacted, redaction

    def chat_participant(self, participant_id: str, role: str, participant_type: str | None = None) -> dict[str, Any]:
        inferred_type = participant_type or ("human" if participant_id in {"operator", "user"} else ("subagent" if participant_id.startswith("subagent") else "agent"))
        return {"id": participant_id, "type": inferred_type, "role": role}

    def chat_export_messages(self, messages: list[dict[str, Any]], *, include_content: bool) -> list[dict[str, Any]]:
        exported: list[dict[str, Any]] = []
        for item in messages:
            body = item.get("message") if isinstance(item.get("message"), dict) else {}
            exported_item = {
                "message_id": item.get("message_id"),
                "session_id": item.get("session_id"),
                "turn_id": item.get("turn_id"),
                "timestamp": item.get("timestamp"),
                "participant": item.get("participant"),
                "message": {
                    "role": body.get("role"),
                    "content_hash": body.get("content_hash"),
                    "redaction": body.get("redaction", "none"),
                },
            }
            if include_content:
                exported_item["message"]["content"] = body.get("content", "")
                exported_item["message"]["content_mode"] = "full" if body.get("redaction") == "none" else body.get("redaction", "redacted")
            else:
                exported_item["message"]["content_mode"] = "metadata_only"
            exported.append(exported_item)
        return exported
