"""Trusted, code-supplied provider policies; incoming events never load code."""
from __future__ import annotations

from dataclasses import dataclass
import re
from types import MappingProxyType
from typing import Any, Iterable, Mapping


@dataclass(frozen=True)
class WorkerBinding:
    run_id: str
    task_id: str
    attempt: str
    session_id: str
    expected_report: str
    category: str
    content: str
    content_hash: str
    summary: str = ""


@dataclass(frozen=True)
class AdapterPolicy:
    provider: str
    adapter: str
    session_mode: str = "ledger"

    def valid_raw_identity(self, envelope: dict[str, Any]) -> bool:
        """Validate provider-owned identity controls, without IO or effects."""
        return False

    def validate(self, envelope: dict[str, Any]) -> bool:
        return False

    def allows_message(self, envelope: dict[str, Any], item: dict[str, Any]) -> bool:
        return False

    def worker_binding(self, envelope: dict[str, Any]) -> WorkerBinding | None:
        return None

    def worker_participant(self, envelope: dict[str, Any], task: dict[str, Any]) -> dict[str, str]:
        return {}

    def owns_report(self, envelope: dict[str, Any], item: dict[str, Any]) -> bool:
        return False

    def fallback_participants(self, envelope: dict[str, Any], item: dict[str, Any]) -> tuple[tuple[str, ...], tuple[str, ...]]:
        return (), ()


@dataclass(frozen=True, init=False)
class AdapterRegistry:
    """An immutable registry built by trusted application setup, not event data."""

    _entries: Mapping[tuple[str, str], AdapterPolicy]

    def __init__(self, policies: Iterable[AdapterPolicy]):
        entries = {}
        for policy in policies:
            if not isinstance(policy, AdapterPolicy) or policy.session_mode not in {"ledger", "worker", "none"}:
                raise ValueError("invalid adapter policy")
            key = (policy.provider, policy.adapter)
            if any(not isinstance(value, str) or not re.fullmatch(r"[a-z0-9][a-z0-9._-]{0,127}", value) for value in key):
                raise ValueError("invalid adapter identity")
            if key in entries:
                raise ValueError("duplicate adapter identity")
            entries[key] = policy
        object.__setattr__(self, "_entries", MappingProxyType(entries))

    @property
    def policies(self) -> tuple[AdapterPolicy, ...]:
        return tuple(self._entries.values())

    def resolve(self, envelope: dict[str, Any]) -> AdapterPolicy | None:
        key = (envelope.get("provider"), envelope.get("adapter"))
        if not all(isinstance(value, str) for value in key):
            return None
        return self._entries.get(key)


def worker_input_summary(run_id: str, task_id: str, attempt: str, payload_hash: str, expected_report: str) -> str:
    return (
        f"ProcessForge launched worker run `{run_id}`, task `{task_id}`, attempt `{attempt}`; "
        f"stdin_payload_hash=`{payload_hash}`; expected_report=`{expected_report}`."
    )


class RuntimeLegacyPolicy(AdapterPolicy):
    """Compatibility for already-normalized input on the authenticated Runtime API."""

    def valid_raw_identity(self, envelope: dict[str, Any]) -> bool:
        raw = envelope.get("raw_payload")
        return (isinstance(raw, dict) and envelope.get("native_id_scope") == "adapter"
                and envelope.get("payload_version") == "1"
                and envelope.get("native_event_id") == raw.get("event_id")
                and envelope.get("native_event_id_stable") is bool(raw.get("event_id")))

    def validate(self, envelope: dict[str, Any]) -> bool:
        return (envelope.get("derived_event") == envelope.get("raw_payload")
                and not envelope.get("derived_conversation_messages"))
