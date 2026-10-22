"""Provenance policy for real Kimi Code host hooks, not worker drivers."""

from __future__ import annotations

from typing import Any

from .kimi_hooks import SUPPORTED_HOOKS, native_envelope
from .provider_adapters import AdapterPolicy


class KimiHooksPolicy(AdapterPolicy):
    def can_register_session(self, envelope: dict[str, Any]) -> bool:
        hook = envelope.get("native_event_type")
        return (
            bool(envelope.get("source_session_id"))
            and isinstance(hook, str)
            and hook in SUPPORTED_HOOKS - {"SessionEnd"}
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
                "provider",
                "adapter",
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
        if derived is not None and derived != expected.get("derived_event"):
            return False
        messages = envelope.get("derived_conversation_messages")
        if messages is not None and messages != expected.get(
            "derived_conversation_messages", []
        ):
            return False
        return True

    def allows_message(self, envelope: dict[str, Any], item: dict[str, Any]) -> bool:
        expected = native_envelope(envelope["raw_payload"]) or {}
        return item in expected.get("derived_conversation_messages", [])
