"""Exercise real source ingress, enrollment, replay and privacy for Kimi."""

from __future__ import annotations

import copy
import json
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
from pf_runtime.host import ingest_event, ledger_session
from pf_runtime.kimi_hooks import _delivery_result, native_envelope
from smoke_conversation_completeness import events, remove_event, transcript


def send(fixture: tuple[Path, Path, Any], payload: dict[str, Any]) -> dict[str, Any]:
    workplace, project, core = fixture
    envelope = native_envelope({**payload, "cwd": str(project)})
    assert envelope is not None
    return ingest_event(envelope, workplace, core)


def test_tool_calls_stay_distinct_and_replay_repairs_missing_effect(
    source_ingress: tuple[Path, Path, Any],
    native_payload: Callable[..., dict[str, Any]],
) -> None:
    session = "kimi-native-tool-session"
    payload = native_payload("PostToolUse", session_id=session, tool_call_id="one")
    first = send(source_ingress, payload)
    second = send(source_ingress, {**payload, "tool_call_id": "two"})
    assert first["routing_status"] == second["routing_status"] == "routed"
    assert first["raw_event_id"] != second["raw_event_id"]
    assert first["normalized_event_ids"] != second["normalized_event_ids"]
    replay = send(source_ingress, payload)
    assert replay["normalized_event_ids"] == first["normalized_event_ids"]
    project = source_ingress[1]
    ids = first["normalized_event_ids"] + second["normalized_event_ids"]
    assert sum(e["event_id"] in ids for e in events(project)) == 2
    remove_event(project, first["normalized_event_ids"][0])
    repaired = send(source_ingress, payload)
    assert repaired["normalized_event_ids"] == first["normalized_event_ids"]
    assert sum(e["event_id"] in ids for e in events(project)) == 2


def test_prompt_enrolls_and_captures_text_once_without_public_content(
    source_ingress: tuple[Path, Path, Any],
    native_payload: Callable[..., dict[str, Any]],
) -> None:
    workplace, project, core = source_ingress
    session = "kimi-native-prompt-session"
    marker = "Private Kimi prompt fixture"
    payload = native_payload(
        "UserPromptSubmit",
        session_id=session,
        prompt=[{"type": "text", "text": marker}],
    )
    first = send(source_ingress, payload)
    repeated = send(source_ingress, payload)
    assert len(first["chat_message_ids"]) == 1
    assert repeated["chat_message_ids"] == first["chat_message_ids"]
    presence = ledger_session(session, workplace, core)
    assert presence
    rows = transcript(project, session)
    assert len(rows) == 1
    message = rows[0]["message"]
    assert isinstance(message, dict)
    assert message["content"] == marker
    assert marker not in json.dumps(events(project))


@pytest.mark.parametrize("hook", ["UserPromptSubmit", "SubagentStop"])
@pytest.mark.parametrize("transport", ["runtime", "ledger-fallback"])
def test_dispatch_accepts_real_conversation_only_receipts(
    source_ingress: tuple[Path, Path, Any],
    native_payload: Callable[..., dict[str, Any]],
    hook: str,
    transport: str,
) -> None:
    """Actual Host receipts keep raw status when capture has no derived event."""
    payload = native_payload(hook, session_id=f"kimi-actual-receipt-{hook}-{transport}")
    first = send(source_ingress, payload)
    replay = send(source_ingress, payload)
    assert first["routing_status"] == "raw_accepted"
    assert replay["routing_status"] == "duplicate_raw"
    assert first["normalized_event_ids"] == replay["normalized_event_ids"] == []
    assert len(first["chat_message_ids"]) == 1
    assert replay["chat_message_ids"] == first["chat_message_ids"]
    for receipt in (first, replay):
        result = _delivery_result(receipt, transport)
        assert result["status"] == "delivered"
        assert result["transport"] == transport
        assert result["chat_message_ids"] == first["chat_message_ids"]
        assert result["routing_status"] == receipt["routing_status"]


def test_subagent_response_captured_under_native_name(
    source_ingress: tuple[Path, Path, Any],
    native_payload: Callable[..., dict[str, Any]],
) -> None:
    session = "kimi-native-subagent-session"
    payload = native_payload("SubagentStop", session_id=session)
    first = send(source_ingress, payload)
    repeated = send(source_ingress, payload)
    assert len(first["chat_message_ids"]) == 1
    assert first["chat_message_ids"] == repeated["chat_message_ids"]
    rows = transcript(source_ingress[1], session)
    assert len(rows) == 1
    message, participant = rows[0]["message"], rows[0]["participant"]
    assert isinstance(message, dict) and isinstance(participant, dict)
    assert message["content"] == payload["response"]
    assert participant["id"] == "subagent:reviewer"


def test_forged_capture_has_no_effects(
    source_ingress: tuple[Path, Path, Any],
    native_payload: Callable[..., dict[str, Any]],
) -> None:
    workplace, project, core = source_ingress
    session = "kimi-forged-session"
    envelope = native_envelope(
        native_payload("UserPromptSubmit", session_id=session, cwd=str(project))
    )
    assert envelope is not None
    forged = copy.deepcopy(envelope)
    forged["derived_conversation_messages"][0]["content"] = "forged capture"
    result = ingest_event(forged, workplace, core)
    assert result["routing_status"] == "denied"
    assert result["diagnostics"]["adapter"]["reason"] == "provenance_rejected"
    assert result["normalized_event_ids"] == result["chat_message_ids"] == []
    assert not ledger_session(session, workplace, core)
    assert transcript(project, session) == []


def test_session_end_checks_out_without_fabricating_answer(
    source_ingress: tuple[Path, Path, Any],
    native_payload: Callable[..., dict[str, Any]],
) -> None:
    session = "kimi-native-end-session"
    send(source_ingress, native_payload("SessionStart", session_id=session))
    ended = send(source_ingress, native_payload("SessionEnd", session_id=session))
    assert ended["routing_status"] == "routed"
    assert len(ended["normalized_event_ids"]) == 1
    assert ended["chat_message_ids"] == []


def test_real_script_captures_prompt_with_an_isolated_offline_runtime(
    source_ingress: tuple[Path, Path, Any],
    native_payload: Callable[..., dict[str, Any]],
) -> None:
    """Exercise the complete hook entry point using only fixture files."""
    project = source_ingress[1]
    script = Path(__file__).resolve().parents[2] / "tools/pf_runtime/kimi_hooks.py"
    session = "kimi-direct-script-session"
    payload = native_payload("UserPromptSubmit", cwd=str(project), session_id=session)
    result = subprocess.run(
        [sys.executable, "-B", str(script)],
        cwd=project,
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        check=False,
        timeout=20,
    )
    assert result.returncode == 0, result.stderr
    rows = transcript(project, session)
    assert len(rows) == 1
    message = rows[0]["message"]
    assert isinstance(message, dict)
    assert message["content"] == "Проверь проект"
