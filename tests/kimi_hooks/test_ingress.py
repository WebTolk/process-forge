"""Exercise real source ingress, enrollment, replay and privacy for Kimi."""

from __future__ import annotations

import copy
import json
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any
from unittest.mock import Mock

import pytest
from pf_runtime.codex_hooks import native_envelope as codex_envelope
from pf_runtime.host import ingest_event, ledger_session
from pf_runtime.kimi_hooks import _delivery_result, native_envelope
from smoke_conversation_completeness import events, pf, remove_event, transcript

import processforge_core.common.clock as clock


def send(
    fixture: tuple[Path, Path, Any], payload: dict[str, Any], provider: str = "kimi"
) -> dict[str, Any]:
    workplace, project, core = fixture
    producer = native_envelope if provider == "kimi" else codex_envelope
    envelope = producer({**payload, "cwd": str(project)})
    assert envelope is not None
    return ingest_event(envelope, workplace, core)


@pytest.mark.parametrize("hook", ["PostToolUse", "SessionStart"])
def test_tool_calls_stay_distinct_and_replay_repairs_missing_effect(
    source_ingress: tuple[Path, Path, Any],
    native_payload: Callable[..., dict[str, Any]],
    monkeypatch: pytest.MonkeyPatch,
    hook: str,
) -> None:
    session = f"kimi-native-{hook}-session"
    payload = native_payload(hook, session_id=session, tool_call_id="one")
    first = send(source_ingress, payload)
    second = send(source_ingress, {**payload, "tool_call_id": "two"})
    assert first["routing_status"] == second["routing_status"] == "routed"
    assert first["raw_event_id"] != second["raw_event_id"]
    assert first["normalized_event_ids"] != second["normalized_event_ids"]
    workplace, project, core = source_ingress
    before_replay = ledger_session(session, workplace, core)
    monkeypatch.setattr(clock, "now_utc", lambda: "2099-01-01T00:00:00Z")
    replay = send(source_ingress, payload)
    assert ledger_session(session, workplace, core) == before_replay
    assert replay["normalized_event_ids"] == first["normalized_event_ids"]
    project = source_ingress[1]
    ids = first["normalized_event_ids"] + second["normalized_event_ids"]
    assert sum(e["event_id"] in ids for e in events(project)) == 2
    remove_event(project, first["normalized_event_ids"][0])
    repaired = send(source_ingress, payload)
    assert ledger_session(session, workplace, core) == before_replay
    assert repaired["normalized_event_ids"] == first["normalized_event_ids"]
    assert sum(e["event_id"] in ids for e in events(project)) == 2


@pytest.mark.parametrize("provider", ["kimi", "codex"])
@pytest.mark.parametrize(
    ("hook", "overrides"),
    [
        ("UserPromptSubmit", {"prompt": "Private native prompt fixture"}),
        ("PreCompact", {}),
        ("PostCompact", {}),
        ("SessionStart", {"source": "compact"}),
        ("PreToolUse", {"tool_name": "Read"}),
        ("PreToolUse", {"tool_name": "Bash"}),
        ("PostToolUse", {}),
        ("PostToolUseFailure", {}),
    ],
)
def test_admitted_activity_refreshes_only_exact_existing_presence(
    source_ingress: tuple[Path, Path, Any],
    native_payload: Callable[..., dict[str, Any]],
    monkeypatch: pytest.MonkeyPatch,
    provider: str,
    hook: str,
    overrides: dict[str, Any],
) -> None:
    if provider == "codex" and hook in {"PreToolUse", "PostToolUseFailure"}:
        pytest.skip("Codex does not support this Kimi hook")
    workplace, project, core = source_ingress
    session = f"{provider}-presence-{hook}-{overrides.get('tool_name', 'default')}"
    other = session + "-other"
    for selected in (session, other):
        send(
            source_ingress,
            native_payload("SessionStart", session_id=selected),
            provider,
        )
    original = ledger_session(session, workplace, core)
    other_original = ledger_session(other, workplace, core)
    payload = native_payload(hook, session_id=session, **overrides)
    pf(
        "config",
        "update",
        "--workplace",
        str(workplace),
        "--key",
        "logging.raw_hooks",
        "--value",
        "false",
    )
    monkeypatch.setattr(clock, "now_utc", lambda: "2099-01-01T00:00:00Z")
    first = send(source_ingress, payload, provider)
    presence = ledger_session(session, workplace, core)
    assert presence["last_seen_at"] == "2099-01-01T00:00:00Z"
    assert original["last_seen_at"] != presence["last_seen_at"]
    assert presence["started_at"] == original["started_at"]
    assert presence["heartbeat_ttl_seconds"] == original["heartbeat_ttl_seconds"]
    assert ledger_session(other, workplace, core) == other_original
    assert first["diagnostics"]["logging"]["raw_hooks"] is False
    monkeypatch.setattr(clock, "now_utc", lambda: "2099-01-02T00:00:00Z")
    repeated = send(source_ingress, payload, provider)
    assert ledger_session(session, workplace, core) == presence
    assert repeated["chat_message_ids"] == first["chat_message_ids"]
    if hook == "UserPromptSubmit":
        assert len(first["chat_message_ids"]) == 1
        rows = transcript(project, session)
        assert len(rows) == 1
        message = rows[0]["message"]
        assert isinstance(message, dict)
        assert message["content"] == overrides["prompt"]
        assert overrides["prompt"] not in json.dumps(events(project))


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


@pytest.mark.parametrize(
    "case",
    [
        "forged",
        "unknown",
        "raw-only",
        "owner",
        "terminal-owner",
        "ambiguous",
        "foreign",
        "unsafe",
        "ended",
    ],
)
def test_rejected_input_preserves_existing_presence(
    source_ingress: tuple[Path, Path, Any],
    native_payload: Callable[..., dict[str, Any]],
    monkeypatch: pytest.MonkeyPatch,
    case: str,
) -> None:
    workplace, project, core = source_ingress
    session = f"kimi-rejected-{case}-session"
    send(
        source_ingress,
        native_payload("SessionStart", session_id=session),
        "codex" if case in {"owner", "terminal-owner"} else "kimi",
    )
    presence = ledger_session(session, workplace, core)
    if case == "ambiguous":
        core.write_agent_presence(workplace, {**presence, "agent_id": "codex"})
    elif case == "foreign":
        presence["project_id"] = "foreign-fixture"
        core.write_agent_presence(workplace, presence)
    elif case == "ended":
        send(source_ingress, native_payload("SessionEnd", session_id=session))
        presence = ledger_session(session, workplace, core)
        assert presence["status"] == "checked_out"
    envelope = native_envelope(
        native_payload(
            "SessionEnd" if case == "terminal-owner" else "UserPromptSubmit",
            session_id=session,
            cwd=str(project),
        )
    )
    assert envelope is not None
    if case == "forged":
        envelope = copy.deepcopy(envelope)
        envelope["derived_conversation_messages"][0]["content"] = "forged capture"
    elif case in {"unknown", "raw-only", "unsafe"}:
        hook = (
            "UnrecognizedFixture"
            if case == "unknown"
            else "Stop"
            if case == "raw-only"
            else "UserPromptSubmit"
        )
        envelope = native_envelope(
            native_payload(
                hook if case == "raw-only" else "UserPromptSubmit",
                hook_event_name=hook,
                session_id=session,
                cwd=str(project),
                prompt="D:/private/fixture",
            )
        )
        assert envelope is not None
    from processforge_core.agents.presence import AgentPresenceReader

    before = AgentPresenceReader(workplace).records()
    monkeypatch.setattr(clock, "now_utc", lambda: "2099-02-01T00:00:00Z")
    result = ingest_event(envelope, workplace, core)
    assert AgentPresenceReader(workplace).records() == before
    assert result["normalized_event_ids"] == result["chat_message_ids"] == []
    assert transcript(project, session) == []
    if case == "foreign":
        with pytest.raises(PermissionError, match="session is not authorized"):
            send(source_ingress, native_payload("PreToolUse", session_id=session))
        assert AgentPresenceReader(workplace).records() == before


def test_session_end_checks_out_without_fabricating_answer(
    source_ingress: tuple[Path, Path, Any],
    native_payload: Callable[..., dict[str, Any]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    checkin = Mock(wraps=source_ingress[2].command_agent_checkin)
    checkout = Mock(wraps=source_ingress[2].command_agent_checkout)
    monkeypatch.setattr(source_ingress[2], "command_agent_checkin", checkin)
    monkeypatch.setattr(source_ingress[2], "command_agent_checkout", checkout)
    session = "kimi-native-end-session"
    send(source_ingress, native_payload("SessionStart", session_id=session))
    ended = send(source_ingress, native_payload("SessionEnd", session_id=session))
    assert ended["routing_status"] == "routed"
    assert len(ended["normalized_event_ids"]) == 1
    assert ended["chat_message_ids"] == []
    workplace, project, core = source_ingress
    presence = ledger_session(session, workplace, core)
    assert presence["status"] == "checked_out"
    monkeypatch.setattr(clock, "now_utc", lambda: "2099-03-01T00:00:00Z")
    remove_event(project, ended["normalized_event_ids"][0])
    repaired = send(source_ingress, native_payload("SessionEnd", session_id=session))
    assert repaired["normalized_event_ids"] == ended["normalized_event_ids"]
    assert any(
        e["event_id"] == ended["normalized_event_ids"][0] for e in events(project)
    )
    assert ledger_session(session, workplace, core) == presence
    for hook in (
        "SessionEnd",
        "UserPromptSubmit",
        "PreToolUse",
        "PostToolUse",
        "SessionStart",
    ):
        send(source_ingress, native_payload(hook, session_id=session))
        assert ledger_session(session, workplace, core) == presence
    assert checkin.call_count == 1
    assert checkout.call_count == 1


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


@pytest.mark.parametrize("hook", ["Stop", "UserPromptSubmit"])
def test_first_raw_only_or_unsafe_input_does_not_enroll(
    source_ingress: tuple[Path, Path, Any],
    native_payload: Callable[..., dict[str, Any]],
    monkeypatch: pytest.MonkeyPatch,
    hook: str,
) -> None:
    workplace, project, core = source_ingress
    session = f"kimi-first-rejected-{hook}"
    checkin = Mock(wraps=core.command_agent_checkin)
    monkeypatch.setattr(core, "command_agent_checkin", checkin)
    assert not ledger_session(session, workplace, core)
    result = send(
        source_ingress,
        native_payload(hook, session_id=session, prompt="D:/private/fixture"),
    )
    assert result["normalized_event_ids"] == result["chat_message_ids"] == []
    if hook == "UserPromptSubmit":
        assert result["diagnostics"]["conversation"] == {
            "status": "denied",
            "reason": "unsafe_automatic_content",
            "sequence": 0,
        }
    assert checkin.call_count == 0
    assert not ledger_session(session, workplace, core)
    assert transcript(project, session) == []


@pytest.mark.parametrize(
    "hook",
    ["SessionStart", "UserPromptSubmit", "PreToolUse", "PostToolUse", "PreCompact"],
)
def test_admitted_first_input_enrolls_once_after_activity_effects(
    source_ingress: tuple[Path, Path, Any],
    native_payload: Callable[..., dict[str, Any]],
    monkeypatch: pytest.MonkeyPatch,
    hook: str,
) -> None:
    workplace, project, core = source_ingress
    session = f"kimi-first-admitted-{hook}"
    checkin_command = core.command_agent_checkin

    def checkin_after_effects(args: Any) -> int:
        assert args.session == session
        if hook == "UserPromptSubmit":
            assert len(transcript(project, session)) == 1
        elif hook != "SessionStart":
            assert any(
                isinstance(value, dict) and value.get("id") == session
                for value in (e.get("session") for e in events(project))
            )
        return int(checkin_command(args))

    checkin = Mock(side_effect=checkin_after_effects)
    monkeypatch.setattr(core, "command_agent_checkin", checkin)
    assert not ledger_session(session, workplace, core)
    payload = native_payload(hook, session_id=session)
    first = send(source_ingress, payload)
    presence = ledger_session(session, workplace, core)
    assert presence["agent_id"] == "kimi"
    assert presence["session_id"] == session
    assert presence["project_id"] == core.project_id(project)
    assert checkin.call_count == 1
    replay = send(source_ingress, payload)
    assert replay["normalized_event_ids"] == first["normalized_event_ids"]
    assert replay["chat_message_ids"] == first["chat_message_ids"]
    assert ledger_session(session, workplace, core) == presence
    assert checkin.call_count == 1


@pytest.mark.parametrize("hook", ["UserPromptSubmit", "PostToolUse"])
def test_non_lifecycle_replay_with_missing_presence_does_not_enroll(
    source_ingress: tuple[Path, Path, Any],
    native_payload: Callable[..., dict[str, Any]],
    monkeypatch: pytest.MonkeyPatch,
    hook: str,
) -> None:
    from processforge_core.agents.presence import AgentPresenceReader

    workplace, project, core = source_ingress
    session = f"kimi-historical-missing-{hook}"
    payload = native_payload(hook, session_id=session)
    first = send(source_ingress, payload)
    assert first["normalized_event_ids"] or first["chat_message_ids"]
    records = AgentPresenceReader.records
    monkeypatch.setattr(
        AgentPresenceReader,
        "records",
        lambda reader: [r for r in records(reader) if r.get("session_id") != session],
    )
    checkin = Mock(wraps=core.command_agent_checkin)
    monkeypatch.setattr(core, "command_agent_checkin", checkin)
    assert not ledger_session(session, workplace, core)
    if hook == "PostToolUse":
        with pytest.raises(PermissionError, match="runtime session is not routed"):
            send(source_ingress, payload)
    else:
        replay = send(source_ingress, payload)
        assert replay["deduplicated"] is True
        assert (
            replay["diagnostics"]["conversation"]["reason"] == "session_not_authorized"
        )
    assert checkin.call_count == 0
    assert not ledger_session(session, workplace, core)


def test_first_capture_failure_does_not_enroll(
    source_ingress: tuple[Path, Path, Any],
    native_payload: Callable[..., dict[str, Any]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from processforge_core.chat.writer import ChatTranscriptWriter

    workplace, _project, core = source_ingress
    session = "kimi-first-capture-failure"
    checkin = Mock(wraps=core.command_agent_checkin)
    monkeypatch.setattr(core, "command_agent_checkin", checkin)
    monkeypatch.setattr(
        ChatTranscriptWriter,
        "append_chat_message",
        Mock(side_effect=OSError("capture failed")),
    )
    with pytest.raises(OSError, match="capture failed"):
        send(source_ingress, native_payload("UserPromptSubmit", session_id=session))
    assert checkin.call_count == 0
    assert not ledger_session(session, workplace, core)


@pytest.mark.parametrize("provider", ["kimi", "codex"])
@pytest.mark.parametrize("hook", ["UserPromptSubmit", "PostToolUse", "PreCompact"])
@pytest.mark.parametrize("binding", ["same", "foreign"])
def test_final_registration_rechecks_interleaved_project_binding(
    source_ingress: tuple[Path, Path, Any],
    native_payload: Callable[..., dict[str, Any]],
    monkeypatch: pytest.MonkeyPatch,
    provider: str,
    hook: str,
    binding: str,
) -> None:
    """An admitted hook can enroll between activity effects and final validation."""
    import pf_runtime.host as host

    workplace, project, core = source_ingress
    session = f"{provider}-final-binding-{hook}-{binding}"
    interleaved_project = project
    if binding == "foreign":
        interleaved_project = project.parent / session
        interleaved_project.mkdir()
        (interleaved_project / "README.md").write_text("# fixture\n", encoding="utf-8")
        pf(
            "project-onboard",
            "--project-root",
            str(interleaved_project),
            "--workplace",
            str(workplace),
            "--type",
            "generic-software-project",
            "--apply",
        )
    checkin = Mock(wraps=core.command_agent_checkin)
    heartbeat = Mock(wraps=core.command_agent_heartbeat)
    checkout = Mock(wraps=core.command_agent_checkout)
    monkeypatch.setattr(core, "command_agent_checkin", checkin)
    monkeypatch.setattr(core, "command_agent_heartbeat", heartbeat)
    monkeypatch.setattr(core, "command_agent_checkout", checkout)
    capture = host._conversation_messages
    interleaved_presence: dict[str, Any] = {}

    def enroll_after_effects(
        *args: Any, **kwargs: Any
    ) -> tuple[list[str], dict[str, Any]]:
        result = capture(*args, **kwargs)
        if args[0].get("source_session_id") == session and kwargs.get(
            "admitted_hook_session"
        ):
            assert not interleaved_presence
            assert not ledger_session(session, workplace, core)
            if hook == "UserPromptSubmit":
                assert len(transcript(project, session)) == 1
            else:
                assert any(
                    isinstance(value, dict) and value.get("id") == session
                    for value in (e.get("session") for e in events(project))
                )
            registered = send(
                (workplace, interleaved_project, core),
                native_payload("SessionStart", session_id=session),
                provider,
            )
            assert registered["routing_status"] == "routed"
            interleaved_presence.update(ledger_session(session, workplace, core))
            assert interleaved_presence["project_id"] == core.project_id(
                interleaved_project
            )
        return result

    monkeypatch.setattr(host, "_conversation_messages", enroll_after_effects)
    assert not ledger_session(session, workplace, core)
    payload = native_payload(hook, session_id=session)
    if binding == "foreign":
        with pytest.raises(
            PermissionError,
            match="^session is not authorized for requested project_root$",
        ):
            send(source_ingress, payload, provider)
    else:
        first = send(source_ingress, payload, provider)
        assert first["normalized_event_ids"] or first["chat_message_ids"]
        assert first["routing_status"] in {"routed", "raw_accepted"}
    assert interleaved_presence["agent_id"] == provider
    assert interleaved_presence["session_id"] == session
    assert not interleaved_presence.get("finished_at")
    assert interleaved_presence["status"] != "checked_out"
    assert ledger_session(session, workplace, core) == interleaved_presence
    assert checkin.call_count == 1
    assert checkin.call_args.args[0].project_id == core.project_id(interleaved_project)
    assert heartbeat.call_count == checkout.call_count == 0
