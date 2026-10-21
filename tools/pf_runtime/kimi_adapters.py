"""Kimi Code hook and PF Kimi-driver provenance policies."""

from __future__ import annotations

from typing import Any

from .kimi_hooks import EVENTS, native_envelope
from .provider_adapters import AdapterPolicy


class KimiHooksPolicy(AdapterPolicy):
    def can_register_session(self, envelope: dict[str, Any]) -> bool:
        hook = envelope.get("native_event_type")
        return bool(envelope.get("source_session_id")) and hook in (
            set(EVENTS) - {"SessionEnd"} | {"UserPromptSubmit", "Stop", "SubagentStop"}
        )

    def valid_raw_identity(self, envelope: dict[str, Any]) -> bool:
        return (
            envelope.get("native_event_id") is None
            and envelope.get("native_id_scope") == "session"
            and envelope.get("native_event_id_stable") is False
            and envelope.get("payload_version") == "kimi-hooks.v1"
        )

    def validate(self, envelope: dict[str, Any]) -> bool:
        raw = envelope.get("raw_payload")
        if not isinstance(raw, dict):
            return False
        expected = native_envelope(raw)
        if expected is None:
            return False
        if any(
            envelope.get(key) != expected.get(key)
            for key in (
                "native_event_type",
                "source_session_id",
                "source_project_ref",
                "native_event_id",
                "native_id_scope",
                "payload_version",
            )
        ):
            return False
        if envelope.get("native_event_id_stable") is not False:
            return False
        derived = envelope.get("derived_event")
        if derived is not None:
            canonical = expected.get("derived_event")
            if not isinstance(derived, dict) or not isinstance(canonical, dict):
                return False
            if any(
                derived.get(key) != canonical.get(key)
                for key in (
                    "event_type",
                    "event_id",
                    "session_id",
                    "project_root",
                    "agent_id",
                )
            ):
                return False
            source = derived.get("source") or {}
            if not isinstance(source, dict) or source.get("adapter") != self.adapter:
                return False
            if any(
                key not in canonical or value != canonical[key]
                for key, value in derived.items()
                if key != "source"
            ):
                return False
            if any(
                value != canonical["source"].get(key) for key, value in source.items()
            ):
                return False
        return True

    def allows_message(self, envelope: dict[str, Any], item: dict[str, Any]) -> bool:
        expected = native_envelope(envelope["raw_payload"]) or {}
        fields = (
            "message_role",
            "participant",
            "content",
            "content_source",
            "turn_id",
            "delivery",
            "parent_message_id",
        )
        return any(
            all(item.get(key) == message.get(key) for key in fields)
            and str(item.get("session_id") or envelope.get("source_session_id") or "")
            == str(message.get("session_id") or "")
            for message in expected.get("derived_conversation_messages", [])
        )

    def fallback_participants(
        self, envelope: dict[str, Any], item: dict[str, Any]
    ) -> tuple[tuple[str, ...], tuple[str, ...]]:
        if (
            envelope.get("native_event_type") == "SessionEnd"
            and item.get("message_role") == "assistant"
        ):
            return ("kimi",), ("subagent",)
        return (), ()
