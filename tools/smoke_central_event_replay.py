#!/usr/bin/env python3
"""Focused smoke for private Codex session raw-v1 replay."""

from __future__ import annotations

import hashlib
import json
import shutil
import sys
import uuid
from pathlib import Path

from processforge_subprocess import diagnostic_text, run_command
from pf_runtime.codex_hooks import runtime_bootstrap
from pf_runtime.raw_ingress_kernel import NativeAgentEvent, RawIngressKernel
import pf_runtime.session_replay as session_replay_module
from pf_runtime.session_replay import checkpoint_path, replay_session_raw_records


ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "tools" / "processforge.py"


def pf(*args: str, expect: int = 0) -> str:
    result = run_command([sys.executable, str(CLI), *args], cwd=ROOT, timeout=120)
    if result.returncode != expect:
        raise AssertionError(f"expected {expect}: {' '.join(args)}\n{diagnostic_text(result)}")
    return result.stdout if expect == 0 else result.stdout + result.stderr


def raw_append(workplace: Path, project: Path, session: str, hook: str, payload: dict[str, object]) -> str:
    receipt = RawIngressKernel(workplace).ingest(
        NativeAgentEvent(
            provider="codex",
            adapter="codex-hooks",
            native_event_type=hook,
            raw_payload=payload,
            payload_version="codex-hooks.v1",
            native_event_id=None,
            native_id_scope="session",
            native_event_id_stable=False,
            source_session_id=session,
            source_project_ref=str(project),
        )
    )
    assert receipt.accepted, receipt
    return str(receipt.raw_event_id)


def existing_runtime_event_id(event_id: str) -> str:
    return "evt_" + hashlib.sha256(event_id.encode("utf-8")).hexdigest()[:32]


def project_event_ids(project: Path, core: object) -> set[str]:
    events_path, _outbox = core.event_runtime_paths(project)
    if not events_path.is_file():
        return set()
    rows = [json.loads(line) for line in events_path.read_text(encoding="utf-8").splitlines() if line]
    return {str(core.event_id_value(row)) for row in rows}


def remove_project_event(project: Path, core: object, event_id: str) -> None:
    events_path, _outbox = core.event_runtime_paths(project)
    rows = [line for line in events_path.read_text(encoding="utf-8").splitlines() if json.loads(line).get("event_id") != event_id]
    events_path.write_text("\n".join(rows) + ("\n" if rows else ""), encoding="utf-8")


def read_checkpoint(workplace: Path, session: str) -> dict[str, object]:
    return json.loads(checkpoint_path(workplace, session).read_text(encoding="utf-8"))


def append_malformed_raw_line(workplace: Path) -> str:
    root = RawIngressKernel(workplace).root
    shards = sorted((root / "raw" / "v1").rglob("*.ndjson"))
    assert shards, "expected at least one raw shard"
    shard = shards[-1]
    offset = shard.stat().st_size
    with shard.open("ab") as handle:
        handle.write(b'{"malformed":\n')
    return f"{shard.relative_to(root).as_posix()}:{offset}"


def assert_failed_repair_checkpoint_stops_at_previous_success(workplace: Path, project: Path, core: object) -> None:
    session = "central-replay-repair-fail"
    raw_append(
        workplace,
        project,
        session,
        "SessionStart",
        {"hook_event_name": "SessionStart", "source": "startup", "cwd": str(project), "session_id": session},
    )
    baseline = replay_session_raw_records(workplace, core, session_id=session, project_ref=str(project))
    assert baseline["status"] == "ok", baseline
    checkpoint_before = read_checkpoint(workplace, session)

    raw_append(
        workplace,
        project,
        session,
        "PostToolUse",
        {"hook_event_name": "PostToolUse", "cwd": str(project), "session_id": session, "turn_id": "turn-fail", "tool_name": "Bash", "tool_use_id": "tool-fail"},
    )
    failing_event = existing_runtime_event_id(f"codex:PostToolUse:{session}:turn-fail:tool-fail")
    original_ingest = session_replay_module._ingest_derived_event

    def failing_ingest(derived: dict[str, object], replay_workplace: Path, replay_core: object, *, project_ref: str) -> dict[str, object]:
        if derived.get("event_id") == f"codex:PostToolUse:{session}:turn-fail:tool-fail":
            raise PermissionError("synthetic repair failure")
        return original_ingest(derived, replay_workplace, replay_core, project_ref=project_ref)

    session_replay_module._ingest_derived_event = failing_ingest
    try:
        failed = replay_session_raw_records(workplace, core, session_id=session, project_ref=str(project))
    finally:
        session_replay_module._ingest_derived_event = original_ingest

    assert failed["status"] == "failed", failed
    assert failed["counts"]["failed"] == 1, failed
    checkpoint_after = read_checkpoint(workplace, session)
    assert checkpoint_after["last_raw_location"] == checkpoint_before["last_raw_location"], checkpoint_after
    assert checkpoint_after["last_raw_event_id"] == checkpoint_before["last_raw_event_id"], checkpoint_after
    assert failing_event not in project_event_ids(project, core)


def assert_malformed_raw_checkpoint_stops_at_previous_success(workplace: Path, project: Path, core: object) -> None:
    session = "central-replay-malformed"
    raw_append(
        workplace,
        project,
        session,
        "SessionStart",
        {"hook_event_name": "SessionStart", "source": "startup", "cwd": str(project), "session_id": session},
    )
    baseline = replay_session_raw_records(workplace, core, session_id=session, project_ref=str(project))
    assert baseline["status"] == "ok", baseline
    checkpoint_before = read_checkpoint(workplace, session)

    malformed_location = append_malformed_raw_line(workplace)
    failed = replay_session_raw_records(workplace, core, session_id=session, project_ref=str(project))
    assert failed["status"] == "failed", failed
    assert failed["counts"]["failed"] == 1, failed
    checkpoint_after = read_checkpoint(workplace, session)
    assert checkpoint_after["last_raw_location"] == checkpoint_before["last_raw_location"], checkpoint_after
    assert checkpoint_after["last_raw_event_id"] == checkpoint_before["last_raw_event_id"], checkpoint_after
    assert checkpoint_after["last_raw_location"] != malformed_location, checkpoint_after


def assert_conversation_replay_repairs_transcript(workplace: Path, project: Path, core: object) -> None:
    session = "central-replay-conversation"
    raw_append(workplace, project, session, "SessionStart", {"hook_event_name": "SessionStart", "source": "startup", "cwd": str(project), "session_id": session})
    raw_append(workplace, project, session, "UserPromptSubmit", {"hook_event_name": "UserPromptSubmit", "cwd": str(project), "session_id": session, "turn_id": "turn-1", "prompt": "Replay this prompt."})
    raw_append(workplace, project, session, "Stop", {"hook_event_name": "Stop", "cwd": str(project), "session_id": session, "turn_id": "turn-1", "last_assistant_message": "Replay this answer."})
    result = replay_session_raw_records(workplace, core, session_id=session, project_ref=str(project))
    assert result["status"] == "ok" and result["counts"]["repaired"] == 3, result
    messages = core.load_chat_messages(project, session)
    assert [item["message"]["content"] for item in messages] == ["Replay this prompt.", "Replay this answer."], messages


def main() -> int:
    runtime = runtime_bootstrap()
    core = runtime.core
    scratch_root = ROOT / ".pf" / "tmp"
    scratch_root.mkdir(parents=True, exist_ok=True)
    root = scratch_root / f"pf-central-replay-{uuid.uuid4().hex}"
    root.mkdir()
    try:
        workplace = root / "workplace"
        first, second = root / "first", root / "second"
        first.mkdir()
        second.mkdir()
        (first / "README.md").write_text("# first\n", encoding="utf-8")
        (second / "README.md").write_text("# second\n", encoding="utf-8")
        pf("workplace-init", "--workplace", str(workplace), "--apply")
        pf("project-onboard", "--project-root", str(first), "--workplace", str(workplace), "--type", "generic-software-project", "--apply")
        pf("project-onboard", "--project-root", str(second), "--workplace", str(workplace), "--type", "generic-software-project", "--apply")

        session = "central-replay-session"
        raw_append(
            workplace,
            first,
            session,
            "SessionStart",
            {"hook_event_name": "SessionStart", "source": "startup", "cwd": str(first), "session_id": session},
        )
        raw_append(
            workplace,
            first,
            session,
            "PostToolUse",
            {"hook_event_name": "PostToolUse", "cwd": str(first), "session_id": session, "turn_id": "turn-1", "tool_name": "Bash", "tool_use_id": "tool-1"},
        )
        raw_append(
            workplace,
            first,
            session,
            "UndocumentedHook",
            {"hook_event_name": "UndocumentedHook", "cwd": str(first), "session_id": session, "value": "kept-raw"},
        )
        raw_append(
            workplace,
            second,
            session,
            "PostToolUse",
            {"hook_event_name": "PostToolUse", "cwd": str(second), "session_id": session, "turn_id": "turn-x", "tool_name": "Bash", "tool_use_id": "tool-x"},
        )
        raw_append(
            workplace,
            second,
            "other-session",
            "SessionStart",
            {"hook_event_name": "SessionStart", "source": "startup", "cwd": str(second), "session_id": "other-session"},
        )

        first_result = replay_session_raw_records(workplace, core, session_id=session, project_ref=str(first))
        assert first_result["status"] == "ok", first_result
        assert first_result["counts"]["seen"] == 4, first_result
        assert first_result["counts"]["repaired"] == 2, first_result
        assert first_result["counts"]["unsupported_mapping"] == 1, first_result
        assert first_result["counts"]["denied"] == 1, first_result

        start_event = existing_runtime_event_id(f"codex:SessionStart:{session}::")
        tool_event = existing_runtime_event_id(f"codex:PostToolUse:{session}:turn-1:tool-1")
        denied_tool_event = existing_runtime_event_id(f"codex:PostToolUse:{session}:turn-x:tool-x")
        assert {start_event, tool_event}.issubset(project_event_ids(first, core))
        assert denied_tool_event not in project_event_ids(second, core)

        checkpoint = json.loads(checkpoint_path(workplace, session).read_text(encoding="utf-8"))
        assert checkpoint["kind"] == "session-replay-checkpoint"
        assert checkpoint["counts"]["denied"] == 1

        second_result = replay_session_raw_records(workplace, core, session_id=session, project_ref=str(first))
        assert second_result["counts"]["present"] == 2, second_result
        assert second_result["counts"]["repaired"] == 0, second_result

        remove_project_event(first, core, tool_event)
        repaired = replay_session_raw_records(workplace, core, session_id=session, project_ref=str(first))
        assert repaired["counts"]["repaired"] == 1, repaired
        assert tool_event in project_event_ids(first, core)

        assert_conversation_replay_repairs_transcript(workplace, first, core)
        assert_failed_repair_checkpoint_stops_at_previous_success(workplace, first, core)
        assert_malformed_raw_checkpoint_stops_at_previous_success(workplace, first, core)

    finally:
        shutil.rmtree(root, ignore_errors=True)
        try:
            scratch_root.rmdir()
        except OSError:
            pass
    print("PASS: central session replay smoke")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
