"""Validate event and chat records with the existing privacy rules."""

from __future__ import annotations

import json
import re
from typing import Any

from .privacy import contains_secret_value


EVENT_TYPE_PATTERN = re.compile(r"^[a-z][a-z0-9_-]*(?:\.[a-z][a-z0-9_-]*)+$")


class RecordValidationPolicy:
    """Apply existing record checks without serialization error translation."""

    def event(self, event: Any, label: str) -> list[str]:
        errors: list[str] = []
        if not isinstance(event, dict):
            return [f"{label}: event is not an object"]
        for key in ["schema_version", "event_id", "event_type", "source", "subject", "time", "correlation_id", "project", "data"]:
            if key not in event:
                errors.append(f"{label}: missing {key}")
        event_type = event.get("event_type")
        if not isinstance(event_type, str) or not EVENT_TYPE_PATTERN.fullmatch(event_type):
            errors.append(f"{label}: invalid event_type")
        serialized = json.dumps(event, ensure_ascii=False)
        if contains_secret_value(serialized):
            errors.append(f"{label}: secret-like value found")
        return errors

    def chat(self, message: Any, label: str) -> list[str]:
        errors: list[str] = []
        if not isinstance(message, dict):
            return [f"{label}: chat message is not an object"]
        for key in ["schema_version", "message_id", "session_id", "turn_id", "timestamp", "participant", "message", "source"]:
            if key not in message:
                errors.append(f"{label}: missing {key}")
        body = message.get("message") if isinstance(message.get("message"), dict) else {}
        if "content_hash" not in body:
            errors.append(f"{label}: missing message.content_hash")
        serialized = json.dumps(message, ensure_ascii=False)
        if contains_secret_value(serialized):
            errors.append(f"{label}: secret-like value found")
        return errors
