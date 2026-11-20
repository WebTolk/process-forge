"""Kimi mapping and provenance checks from actual producer payload shapes."""

from __future__ import annotations

import copy
from collections.abc import Callable
from typing import Any

import pytest
from pf_runtime.kimi_adapters import KimiHooksPolicy
from pf_runtime.kimi_hooks import native_envelope, normalized_event


def envelope(payload: dict[str, Any]) -> dict[str, Any]:
    result = native_envelope(payload)
    assert result is not None
    return result


@pytest.mark.parametrize(
    ("hook", "tool", "event_type"),
    [
        ("PreToolUse", "Read", "agent.tool.started"),
        ("PreToolUse", "Bash", "agent.command.started"),
        ("PostToolUse", "Read", "agent.tool.completed"),
        ("PostToolUse", "Bash", "agent.command.completed"),
        ("PostToolUseFailure", "Read", "agent.tool.completed"),
        ("PostToolUseFailure", "Bash", "agent.command.completed"),
    ],
)
def test_actual_tool_fields(
    native_payload: Callable[..., dict[str, Any]], hook: str, tool: str, event_type: str
) -> None:
    event = normalized_event(native_payload(hook, tool_name=tool))
    assert event is not None
    assert event["event_type"] == event_type
    assert event["payload"]["tool_call_id"]
    assert "tool_use_id" not in event["payload"]
    assert "tool_input" not in event["payload"]
    assert "tool_output" not in event["payload"]
    assert "error" not in event["payload"]
    if hook == "PostToolUseFailure":
        assert event["payload"]["status"] == "failed"


def test_distinct_tool_occurrences_and_exact_replay(
    native_payload: Callable[..., dict[str, Any]],
) -> None:
    first = native_payload("PostToolUse", tool_call_id="call-one")
    second = native_payload("PostToolUse", tool_call_id="call-two")
    assert normalized_event(first) != normalized_event(second)
    assert normalized_event(first) == normalized_event(copy.deepcopy(first))


def test_idless_compactions_use_canonical_payload_identity(
    native_payload: Callable[..., dict[str, Any]],
) -> None:
    first = native_payload("PreCompact", token_count=12000)
    second = native_payload("PreCompact", token_count=18000)
    a, b = normalized_event(first), normalized_event(second)
    assert a is not None and b is not None
    assert a["event_id"] != b["event_id"]
    assert a == normalized_event(dict(reversed(list(first.items()))))


@pytest.mark.parametrize(
    ("content", "expected"),
    [
        (
            [{"type": "text", "text": "Привет"}, {"type": "text", "text": " 🌍"}],
            "Привет 🌍",
        ),
        (
            [{"type": "image", "data": "synthetic"}, {"type": "text", "text": "Text"}],
            "Text",
        ),
        ("Text", "Text"),
        ([{"type": "text", "text": 7}], None),
        ([{"type": "image", "data": "synthetic"}], None),
        ([None, 42, "not a content part"], None),
        ({"text": "not a content array"}, None),
        ([], None),
    ],
)
def test_prompt_text_parts(
    native_payload: Callable[..., dict[str, Any]], content: Any, expected: str | None
) -> None:
    result = envelope(native_payload("UserPromptSubmit", prompt=content))
    messages = result.get("derived_conversation_messages", [])
    if expected is None:
        assert messages == []
    else:
        assert len(messages) == 1
        assert messages[0]["content"] == expected
        assert messages[0]["turn_id"] is None
        assert messages[0]["message_role"] == "user"
    assert result["raw_payload"]["prompt"] == content


def test_subagent_response_and_real_name(
    native_payload: Callable[..., dict[str, Any]],
) -> None:
    result = envelope(native_payload("SubagentStop"))
    item = result["derived_conversation_messages"][0]
    assert item["content"] == "Проверка завершена"
    assert item["participant"] == {
        "id": "subagent:reviewer",
        "type": "subagent",
        "role": "subagent",
    }


@pytest.mark.parametrize("hook", ["Stop", "SessionEnd"])
def test_no_invented_primary_assistant_text(
    native_payload: Callable[..., dict[str, Any]], hook: str
) -> None:
    result = envelope(native_payload(hook, last_assistant_message="foreign field"))
    assert "derived_conversation_messages" not in result


@pytest.mark.parametrize("field", ["cwd", "session_id"])
def test_incomplete_native_identity_has_no_effect(
    native_payload: Callable[..., dict[str, Any]], field: str
) -> None:
    payload = native_payload("PostToolUse", **{field: 7})
    assert normalized_event(payload) is None
    result = native_envelope(payload)
    assert result is None or result["derived_event"] is None


def test_unverified_aliases_do_not_enroll() -> None:
    assert (
        native_envelope(
            {"event": "SessionStart", "project_root": "fixture", "sid": "x"}
        )
        is None
    )


@pytest.mark.parametrize(
    "hook",
    [
        "SessionStart",
        "PostToolUse",
        "UserPromptSubmit",
        "SubagentStop",
        "Stop",
        "SessionEnd",
    ],
)
def test_native_policy_and_enrollment(
    native_payload: Callable[..., dict[str, Any]], hook: str
) -> None:
    result = envelope(native_payload(hook))
    policy = KimiHooksPolicy("kimi", "kimi-hooks")
    assert policy.valid_raw_identity(result)
    assert policy.validate(result)
    assert policy.can_register_session(result) is (hook != "SessionEnd")
    for item in result.get("derived_conversation_messages", []):
        assert policy.allows_message(result, item)


@pytest.mark.parametrize(
    "target", ["payload", "source", "event_id", "message", "participant"]
)
def test_forged_derivations_rejected(
    native_payload: Callable[..., dict[str, Any]], target: str
) -> None:
    hook = "UserPromptSubmit" if target in {"message", "participant"} else "PostToolUse"
    result = envelope(native_payload(hook))
    if target == "payload":
        result["derived_event"]["payload"]["tool_call_id"] = "forged"
    elif target == "source":
        result["derived_event"]["source"]["adapter"] = "codex-hooks"
    elif target == "event_id":
        result["derived_event"]["event_id"] = "forged"
    elif target == "message":
        result["derived_conversation_messages"][0]["content"] = "forged"
    else:
        result["derived_conversation_messages"][0]["participant"]["id"] = "forged"
    assert not KimiHooksPolicy("kimi", "kimi-hooks").validate(result)
