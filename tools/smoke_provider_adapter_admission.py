#!/usr/bin/env python3
"""Exercise trusted custom provider admission through the real Runtime Host."""

from __future__ import annotations

import hashlib
import json
import sys
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from pf_runtime.builtin_provider_adapters import DEFAULT_ADAPTER_REGISTRY
from pf_runtime.codex_hooks import native_envelope
from pf_runtime.host import ingest_event
from pf_runtime.provider_adapters import AdapterPolicy, AdapterRegistry
from pf_runtime.session_replay import replay_session_raw_records
from smoke_conversation_completeness import setup_basic_project, events, remove_event, transcript


class FixturePolicy(AdapterPolicy):
    """A deliberately explicit, trusted test integration."""

    def __init__(self) -> None:
        super().__init__("fixture-agent", "fixture-native")

    def valid_raw_identity(self, envelope: dict[str, Any]) -> bool:
        return (envelope.get("native_id_scope") == "project"
                and envelope.get("native_event_id_stable") is True
                and envelope.get("payload_version") == "1"
                and isinstance(envelope.get("native_event_id"), str)
                and bool(envelope.get("native_event_id")))

    def validate(self, envelope: dict[str, Any]) -> bool:
        raw = envelope.get("raw_payload")
        if not isinstance(raw, dict):
            return False
        if raw.get("source_session_id") != envelope.get("source_session_id"):
            return False
        if raw.get("source_project_ref") != envelope.get("source_project_ref"):
            return False
        if raw.get("native_event_type") != envelope.get("native_event_type"):
            return False
        derived = envelope.get("derived_event")
        if isinstance(derived, dict):
            if (derived.get("project_root") != envelope.get("source_project_ref")
                    or derived.get("session_id") != envelope.get("source_session_id")
                    or derived.get("source", {}).get("session_id") != envelope.get("source_session_id")):
                return False
            if raw.get("native_event_type") != "SessionStart":
                return False
        messages = envelope.get("derived_conversation_messages") or []
        for item in messages:
            if (not isinstance(item, dict) or item.get("session_id") != envelope.get("source_session_id")
                    or item.get("content") != raw.get("content")
                    or item.get("content_source", {}).get("provider") != "fixture-agent"
                    or item.get("content_source", {}).get("adapter") != "fixture-native"
                    or item.get("content_source", {}).get("native_event_type") != envelope.get("native_event_type")):
                return False
        return True

    def allows_message(self, envelope: dict[str, Any], item: dict[str, Any]) -> bool:
        raw = envelope.get("raw_payload", {})
        return (item.get("content") == raw.get("content")
                and item.get("session_id") == envelope.get("source_session_id"))


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def snapshot(paths: list[Path]) -> dict[str, str]:
    return {str(path): hashlib.sha256(path.read_bytes()).hexdigest() for path in paths}


def native(project: Path, session: str, event_type: str, event_id: str,
            raw: dict[str, Any], *, derived: dict[str, Any] | None = None,
            messages: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    return {
        "provider": "fixture-agent", "adapter": "fixture-native",
        "native_event_type": event_type, "native_event_id": event_id,
        "native_id_scope": "project", "native_event_id_stable": True,
        "source_session_id": session, "source_project_ref": str(project),
        "payload_version": "1", "raw_payload": raw,
        **({"derived_event": derived} if derived is not None else {}),
        **({"derived_conversation_messages": messages} if messages is not None else {}),
    }


def raw_for(project: Path, session: str, event_type: str, content: str = "") -> dict[str, Any]:
    return {"source_session_id": session, "source_project_ref": str(project),
            "native_event_type": event_type, "content": content}


def start_envelope(project: Path, session: str, event_id: str = "start-1") -> dict[str, Any]:
    raw = raw_for(project, session, "SessionStart")
    return native(project, session, "SessionStart", event_id, raw, derived={
        "schema_version": 1, "event_type": "agent.session.started",
        "event_id": f"fixture:SessionStart:{session}", "project_root": str(project),
        "session_id": session, "agent_id": "fixture-agent",
        "source": {"adapter": "fixture-native", "session_id": session},
    })


def message_envelope(project: Path, session: str, event_id: str, content: str) -> dict[str, Any]:
    raw = raw_for(project, session, "Message", content)
    item = {
        "message_role": "user", "participant": {"id": "fixture-user", "type": "user", "role": "user"},
        "session_id": session, "turn_id": event_id, "content": content,
        "content_source": {"kind": "fixture-message", "provider": "fixture-agent",
                           "adapter": "fixture-native", "native_event_type": "Message"},
        "delivery": {"state": "complete", "sequence": 1, "final": True},
    }
    return native(project, session, "Message", event_id, raw, messages=[item])


def run() -> None:
    host_file = ROOT / "tools" / "pf_runtime" / "host.py"
    kernel_file = ROOT / "tools" / "pf_runtime" / "raw_ingress_kernel.py"
    replay_file = ROOT / "tools" / "pf_runtime" / "session_replay.py"
    source_files = [host_file, kernel_file, replay_file]
    before = snapshot(source_files)
    with tempfile.TemporaryDirectory(prefix="pf-provider-admission-") as temp:
        temp_root = Path(temp)
        workplace, project = setup_basic_project(temp_root, "provider-project")
        import processforge as core

        policy = FixturePolicy()
        registry = AdapterRegistry(tuple([*DEFAULT_ADAPTER_REGISTRY.policies, policy]))
        session = "fixture-session"
        accepted_start = ingest_event(start_envelope(project, session), workplace, core, registry=registry)
        require(accepted_start.get("routing_status") == "routed"
                and len(accepted_start.get("normalized_event_ids", [])) == 1,
                f"custom provider start was not admitted: {accepted_start}")
        start_id = accepted_start["normalized_event_ids"][0]
        remove_event(project, start_id)
        repaired = ingest_event(start_envelope(project, session), workplace, core, registry=registry)
        require(repaired.get("routing_status") == "routed"
                and repaired.get("normalized_event_ids") == [start_id]
                and sum(1 for row in events(project) if row.get("event_id") == start_id) == 1,
                f"duplicate replay did not repair the removed derived effect exactly once: {repaired}")

        message = message_envelope(project, session, "message-1", "hello from fixture")
        first = ingest_event(message, workplace, core, registry=registry)
        repeated = ingest_event(message, workplace, core, registry=registry)
        require(len(first.get("chat_message_ids", [])) == 1
                and repeated.get("chat_message_ids") == first.get("chat_message_ids")
                and len(transcript(project, session)) == 1,
                f"custom provider message/replay was not idempotent: first={first}; replay={repeated}")

        def denied(envelope: dict[str, Any], reason: str, label: str) -> None:
            result = ingest_event(envelope, workplace, core, registry=registry)
            require(result.get("accepted") is True and result.get("routing_status") == "denied"
                    and result.get("normalized_event_ids") == [] and result.get("chat_message_ids") == []
                    and result.get("diagnostics", {}).get("adapter", {}).get("reason") == reason,
                    f"{label} should retain raw receipt but deny effects: {result}")

        spoof = start_envelope(project, "spoof-session", "spoof-1")
        spoof["provider"] = "untrusted-agent"
        denied(spoof, "adapter_untrusted", "unknown provider")
        unknown_adapter = start_envelope(project, "unknown-adapter-session", "unknown-adapter-1")
        unknown_adapter["adapter"] = "unknown-adapter"
        denied(unknown_adapter, "adapter_untrusted", "unknown adapter")

        mismatch_cases: list[tuple[str, dict[str, Any]]] = []
        wrong_session = start_envelope(project, "session-a", "bad-session-1")
        wrong_session["derived_event"]["session_id"] = "session-b"
        mismatch_cases.append(("derived session mismatch", wrong_session))
        wrong_source = start_envelope(project, "source-session", "bad-source-1")
        wrong_source["raw_payload"]["source_project_ref"] = str(temp_root / "elsewhere")
        mismatch_cases.append(("source project metadata mismatch", wrong_source))
        wrong_content = message_envelope(project, session, "bad-content-1", "raw content")
        wrong_content["derived_conversation_messages"][0]["content"] = "changed content"
        mismatch_cases.append(("message content mismatch", wrong_content))
        for label, envelope in mismatch_cases:
            denied(envelope, "provenance_rejected", label)

        partial_native = {
            "provider": "fixture-agent", "event_type": "agent.session.started",
            "event_id": "partial-native-must-not-route", "project_root": str(project),
            "session_id": "partial-native-session",
        }
        partial_result = ingest_event(partial_native, workplace, core, registry=registry)
        require(partial_result.get("accepted") is True and partial_result.get("routing_status") == "denied"
                and partial_result.get("normalized_event_ids") == [] and partial_result.get("chat_message_ids") == [],
                f"partial native claim fell through to legacy normalized routing: {partial_result}")

        forged_cases: list[tuple[str, dict[str, Any]]] = []
        forged_agent = native_envelope({"hook_event_name": "SessionStart", "cwd": str(project), "session_id": "forged-agent-session"})
        require(forged_agent is not None, "Codex SessionStart envelope builder returned no envelope")
        forged_agent["derived_event"]["source"]["agent"] = "spoofed-agent"
        forged_cases.append(("forged Codex source agent", forged_agent))
        forged_payload = native_envelope({"hook_event_name": "SessionStart", "cwd": str(project), "session_id": "forged-payload-session"})
        require(forged_payload is not None, "Codex SessionStart envelope builder returned no envelope")
        forged_payload["derived_event"]["payload"] = {"untrusted": True}
        forged_cases.append(("forged Codex derived payload", forged_payload))
        for label, envelope in forged_cases:
            result = ingest_event(envelope, workplace, core)
            require(result.get("accepted") is True and result.get("routing_status") == "denied"
                    and result.get("normalized_event_ids") == [] and result.get("chat_message_ids") == []
                    and result.get("diagnostics", {}).get("adapter", {}).get("reason") == "provenance_rejected",
                    f"{label} should retain raw receipt but deny effects: {result}")

        replay_session = "codex-identity-replay-session"
        codex_start = native_envelope({"hook_event_name": "SessionStart", "cwd": str(project), "session_id": replay_session})
        require(codex_start is not None, "Codex SessionStart envelope builder returned no envelope")
        start_result = ingest_event(codex_start, workplace, core)
        require(start_result.get("routing_status") == "routed", f"Codex replay fixture session failed to start: {start_result}")
        identity_mutations = {
            "native_event_id": "forged-native-id",
            "native_id_scope": "project",
            "native_event_id_stable": True,
            "payload_version": "spoofed-codex-hooks.v9",
        }
        forged_raw_ids: set[str] = set()
        for index, (field, value) in enumerate(identity_mutations.items(), start=1):
            prompt = native_envelope({"hook_event_name": "UserPromptSubmit", "cwd": str(project),
                                      "session_id": replay_session, "turn_id": f"identity-turn-{index}",
                                      "prompt": f"forged identity {field}"})
            require(prompt is not None, f"Codex prompt builder returned no envelope for {field}")
            prompt[field] = value
            result = ingest_event(prompt, workplace, core)
            require(result.get("accepted") is True and result.get("routing_status") == "denied"
                    and result.get("normalized_event_ids") == [] and result.get("chat_message_ids") == []
                    and result.get("diagnostics", {}).get("adapter", {}).get("reason") == "provenance_rejected",
                    f"forged Codex {field} should retain raw but deny effects: {result}")
            forged_raw_ids.add(str(result.get("raw_event_id") or ""))

        replay = replay_session_raw_records(workplace, core, session_id=replay_session, project_ref=str(project))
        denied_ids = {str(item.get("raw_event_id") or "") for item in replay.get("records", [])
                      if item.get("status") == "denied" and item.get("code") == "provenance_rejected"}
        require(replay.get("status") == "ok" and forged_raw_ids <= denied_ids,
                f"session replay did not reject all forged Codex identity records: {replay}")
        replay_rows = transcript(project, replay_session)
        require(not any(row.get("message", {}).get("content", "").startswith("forged identity ") for row in replay_rows),
                f"session replay created a chat message from forged Codex identity: {replay_rows}")

        collision_base = message_envelope(project, session, "collision-native", "original")
        collision_ok = ingest_event(collision_base, workplace, core, registry=registry)
        require(collision_ok.get("accepted") is True, f"collision baseline raw event rejected: {collision_ok}")
        collision = message_envelope(project, session, "collision-native", "altered")
        collision_result = ingest_event(collision, workplace, core, registry=registry)
        require(collision_result.get("accepted") is False
                and collision_result.get("routing_status") == "quarantined"
                and collision_result.get("diagnostics", {}).get("code") == "native_id_payload_conflict",
                f"conflicting native identity was not quarantined: {collision_result}")

        try:
            AdapterRegistry(tuple([*DEFAULT_ADAPTER_REGISTRY.policies, policy, FixturePolicy()]))
        except ValueError as exc:
            require("duplicate adapter identity" in str(exc), f"unexpected duplicate-registration error: {exc}")
        else:
            raise AssertionError("duplicate trusted adapter registration unexpectedly succeeded")
        try:
            AdapterRegistry((object(),))  # type: ignore[arg-type]
        except ValueError:
            pass
        else:
            raise AssertionError("non-policy registration unexpectedly succeeded")

    after = snapshot(source_files)
    require(before == after, "the regression modified Host or RawIngressKernel source")
    print("PASS: trusted custom provider start/message, duplicate replay repair/idempotence, untrusted identity/provenance denial, forged Codex identity replay denial, partial-native raw-only denial, native-ID quarantine, duplicate registry rejection, Host/kernel/replay sources unchanged")


if __name__ == "__main__":
    run()
