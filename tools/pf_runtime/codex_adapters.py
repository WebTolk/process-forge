"""Codex hook and PF Codex-driver provenance policies."""
from __future__ import annotations

import hashlib
from typing import Any

from .codex_hooks import native_envelope
from .provider_adapters import AdapterPolicy, WorkerBinding, worker_input_summary


class CodexHooksPolicy(AdapterPolicy):
    def valid_raw_identity(self, envelope: dict[str, Any]) -> bool:
        return (envelope.get("native_event_id") is None and envelope.get("native_id_scope") == "session"
                and envelope.get("native_event_id_stable") is False and envelope.get("payload_version") == "codex-hooks.v1")

    def validate(self, envelope: dict[str, Any]) -> bool:
        raw = envelope.get("raw_payload")
        if not isinstance(raw, dict):
            return False
        expected = native_envelope(raw)
        if expected is None:
            return False
        if any(envelope.get(key) != expected.get(key) for key in ("native_event_type", "source_session_id", "source_project_ref", "native_event_id", "native_id_scope", "payload_version")):
            return False
        if envelope.get("native_event_id_stable") is not False:
            return False
        derived = envelope.get("derived_event")
        if derived is not None:
            canonical = expected.get("derived_event")
            if not isinstance(derived, dict) or not isinstance(canonical, dict):
                return False
            if any(derived.get(key) != canonical.get(key) for key in ("event_type", "event_id", "session_id", "project_root", "agent_id")):
                return False
            source = derived.get("source") or {}
            if not isinstance(source, dict) or source.get("adapter") != self.adapter:
                return False
            if any(key not in canonical or value != canonical[key] for key, value in derived.items() if key != "source"):
                return False
            if any(value != canonical["source"].get(key) for key, value in source.items()):
                return False
        return True

    def allows_message(self, envelope: dict[str, Any], item: dict[str, Any]) -> bool:
        expected = native_envelope(envelope["raw_payload"]) or {}
        fields = ("message_role", "participant", "content", "content_source", "turn_id", "delivery", "parent_message_id")
        return any(all(item.get(key) == message.get(key) for key in fields)
                   and str(item.get("session_id") or envelope.get("source_session_id") or "") == str(message.get("session_id") or "")
                   for message in expected.get("derived_conversation_messages", []))

    def fallback_participants(self, envelope: dict[str, Any], item: dict[str, Any]) -> tuple[tuple[str, ...], tuple[str, ...]]:
        if envelope.get("native_event_type") == "SessionEnd" and item.get("message_role") == "assistant":
            return ("codex",), ("subagent",)
        return (), ()


class CodexWorkerPolicy(AdapterPolicy):
    def valid_raw_identity(self, envelope: dict[str, Any]) -> bool:
        return (envelope.get("native_id_scope") == "project" and envelope.get("native_event_id_stable") is True
                and envelope.get("payload_version") == "1")

    def worker_binding(self, envelope: dict[str, Any]) -> WorkerBinding | None:
        raw = envelope.get("raw_payload")
        if not isinstance(raw, dict):
            return None
        run_id, task_id, attempt = (str(raw.get(key) or "") for key in ("run_id", "task_id", "attempt"))
        session = f"pf-worker:{run_id}:{task_id}:attempt:{attempt}"
        report = str(raw.get("expected_report") or "")
        event = envelope.get("native_event_type")
        if event == "WorkerPromptPayloadSubmitted":
            content, digest = raw.get("stdin_payload"), raw.get("stdin_payload_hash")
            summary = worker_input_summary(run_id, task_id, attempt, str(digest or ""), report)
            category = "input"
        elif event == "WorkerExpectedReportCaptured":
            content, digest, summary, category = raw.get("report_content"), raw.get("report_hash"), "", "output"
        else:
            return None
        if not isinstance(content, str) or not isinstance(digest, str):
            return None
        return WorkerBinding(run_id, task_id, attempt, session, report, category, content, digest, summary)

    def validate(self, envelope: dict[str, Any]) -> bool:
        binding = self.worker_binding(envelope)
        if binding is None or envelope.get("derived_event") is not None:
            return False
        if (envelope.get("native_id_scope") != "project" or envelope.get("native_event_id_stable") is not True
                or envelope.get("payload_version") != "1"):
            return False
        prefix = "worker-input" if binding.category == "input" else "worker-output"
        expected = f"{prefix}:{binding.run_id}:{binding.task_id}:attempt:{binding.attempt}"
        if binding.category == "output":
            expected += ":" + binding.content_hash
        return (envelope.get("source_session_id") == binding.session_id
                and envelope.get("native_event_id") == expected
                and binding.content_hash == "sha256:" + hashlib.sha256(binding.content.encode("utf-8")).hexdigest())

    def allows_message(self, envelope: dict[str, Any], item: dict[str, Any]) -> bool:
        binding = self.worker_binding(envelope)
        if binding is None:
            return False
        source = item.get("content_source") or {}
        if binding.category == "input":
            expected = ("system", "pf_codex_exec_input", "pf_owned_safe_summary", binding.summary)
        else:
            expected = ("assistant", "pf_codex_exec_output", "pf_owned_output_file", binding.content)
        return (isinstance(source, dict) and (item.get("message_role"), source.get("kind"), source.get("content_provenance"), item.get("content")) == expected
                and str(item.get("session_id") or binding.session_id) == binding.session_id
                and item.get("turn_id") == f"worker-turn:{binding.run_id}:{binding.task_id}:attempt:{binding.attempt}"
                and item.get("delivery") == {"state": "complete", "sequence": 0 if binding.category == "input" else 1, "final": True}
                and item.get("parent_message_id") is None)

    def worker_participant(self, envelope: dict[str, Any], task: dict[str, Any]) -> dict[str, str]:
        binding = self.worker_binding(envelope)
        if binding is None:
            return {}
        if binding.category == "input":
            return {"id": "processforge-runtime", "type": "agent", "role": "worker_launcher"}
        ownership = task.get("ownership") or {}
        return {"id": str(ownership.get("owner_id") or "worker"), "type": "agent", "role": "worker"}

    def owns_report(self, envelope: dict[str, Any], item: dict[str, Any]) -> bool:
        binding = self.worker_binding(envelope)
        return binding is not None and binding.category == "output"
