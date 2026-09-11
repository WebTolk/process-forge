#!/usr/bin/env python3
"""Regression smoke for exact, opaque agent-session identity round trips."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PF = ROOT / "tools" / "processforge.py"
sys.path.insert(0, str(ROOT / "tools"))

import processforge as core
from pf_runtime.session_read import session_chat_payload, session_context_payload


def cli(*args: str, expect: int = 0) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        [sys.executable, str(PF), *args],
        cwd=ROOT,
        text=True,
        encoding="utf-8",
        errors="strict",
        capture_output=True,
        timeout=120,
    )
    if result.returncode != expect:
        raise AssertionError(f"expected {expect}, got {result.returncode}: {result.stdout}{result.stderr}")
    return result


def presence_payload(agent_id: str, session_id: str, project: Path) -> dict[str, object]:
    now = core.now_utc()
    return {
        "schema_version": 1,
        "agent_id": agent_id,
        "session_id": session_id,
        "status": "online",
        "project_id": core.project_id(project),
        "project_root": str(project),
        "last_seen_at": now,
        "heartbeat_ttl_seconds": 300,
    }


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="pf-session-identity-") as raw:
        root = Path(raw)
        workplace = root / "workplace"
        project = root / "project"
        project.mkdir()
        cli("workplace-init", "--workplace", str(workplace), "--apply")
        cli("project-onboard", "--project-root", str(project), "--workplace", str(workplace), "--type", "generic", "--apply")

        sessions = ["lower-session", "Case-Session", "slug/a", "slug-a"]
        agent = "fixture-agent"
        for session_id in sessions:
            cli(
                "agent-checkin",
                "--workplace",
                str(workplace),
                "--project-root",
                str(project),
                "--agent",
                agent,
                "--session",
                session_id,
            )
            core.append_chat_message(
                project,
                session_id=session_id,
                participant_id="fixture-agent",
                participant_role="worker",
                message_role="assistant",
                content=f"message for {session_id}",
            )

        paths = {core.agent_presence_path(workplace, agent, session_id) for session_id in sessions}
        if len(paths) != len(sessions) or not all(path.is_file() for path in paths):
            raise AssertionError("exact session identities did not receive distinct presence files")

        for session_id in sessions:
            presence = core.find_agent_presence(workplace, session_id=session_id)
            if presence.get("session_id") != session_id:
                raise AssertionError(f"presence lookup lost exact identity: {session_id!r}: {presence}")
            context = session_context_payload(workplace, core, session_id=session_id)
            if context["session"]["id"] != session_id:
                raise AssertionError(f"session context lost exact identity: {session_id!r}")
            chat = session_chat_payload(workplace, core, session_id=session_id)
            messages = chat.get("messages") if isinstance(chat, dict) else None
            if not isinstance(messages, list) or len(messages) != 1 or messages[0].get("session_id") != session_id:
                raise AssertionError(f"session chat was not isolated: {session_id!r}: {json.dumps(chat)}")
            request = {"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {"name": "pf.session_context", "arguments": {}}}
            wire = subprocess.run([sys.executable, str(ROOT / "tools/pf_runtime/mcp_server.py"), "--workplace", str(workplace), "--session", session_id],
                                  input=json.dumps(request)+"\n", text=True, capture_output=True, timeout=30)
            assert wire.returncode == 0, wire.stderr
            response = json.loads(wire.stdout)
            assert not response["result"].get("isError"), response
            native_context = json.loads(response["result"]["content"][0]["text"])
            assert native_context["session"]["id"] == session_id, native_context

        cli("agent-checkout", "--workplace", str(workplace), "--session", "slug/a")
        if core.find_agent_presence(workplace, session_id="slug/a").get("status") != "checked_out":
            raise AssertionError("checkout did not update the selected exact session")
        if core.find_agent_presence(workplace, session_id="slug-a").get("status") != "online":
            raise AssertionError("checkout of colliding slug session changed its sibling")

        legacy = presence_payload("legacy-agent", "Legacy/Session", project)
        legacy_path = core.workplace_agent_presence_dir(workplace) / "legacy-agent" / "legacy-session.json"
        legacy_path.parent.mkdir(parents=True, exist_ok=True)
        legacy_path.write_text(json.dumps(legacy), encoding="utf-8")
        if core.find_agent_presence(workplace, session_id="Legacy/Session").get("session_id") != "Legacy/Session":
            raise AssertionError("valid legacy mixed-case/session fixture was not readable")
        cli("agent-heartbeat", "--workplace", str(workplace), "--session", "Legacy/Session")
        assert core.find_agent_presence(workplace, session_id="Legacy/Session").get("status") == "online"
        cli("agent-checkout", "--workplace", str(workplace), "--session", "Legacy/Session")
        assert core.find_agent_presence(workplace, session_id="Legacy/Session").get("status") == "checked_out"
        assert len([item for item in core.iter_agent_presence(workplace) if item.get("session_id") == "Legacy/Session"]) == 1
        old_chat = core.legacy_chat_transcript_path(project, "Legacy/Session")
        old_chat.parent.mkdir(parents=True, exist_ok=True)
        old_record = {"message_id": "legacy-message", "session_id": "Legacy/Session", "message": {"role": "assistant", "content": "legacy content"}}
        foreign_record = {"message_id": "foreign-message", "session_id": "legacy-session", "message": {"role": "assistant", "content": "foreign content"}}
        old_chat.write_text(json.dumps(old_record)+"\n"+json.dumps(foreign_record)+"\n", encoding="utf-8")
        core.append_chat_message(project, session_id="Legacy/Session", participant_id="fixture", participant_role="worker", message_role="assistant", content="new content")
        history = core.load_chat_messages(project, "Legacy/Session")
        assert [item["message"]["content"] for item in history] == ["legacy content", "new content"], history
        core.append_chat_message(project, session_id="Legacy/Session", participant_id="fixture", participant_role="worker", message_role="assistant", content="legacy content", message_id="legacy-message")
        assert len(core.load_chat_messages(project, "Legacy/Session")) == 2

        forged = presence_payload("forged-agent", "other-session", project)
        forged_path = core.workplace_agent_presence_dir(workplace) / "forged-agent" / "forged-session.json"
        forged_path.parent.mkdir(parents=True, exist_ok=True)
        forged_path.write_text(json.dumps(forged), encoding="utf-8")
        if core.find_agent_presence(workplace, agent_id="forged-agent", session_id="forged-session"):
            raise AssertionError("forged legacy metadata was accepted for the filename identity")
        assert not core.find_agent_presence(workplace, agent_id="forged-agent", session_id="other-session")

    print("PASS: exact opaque session identity round trip")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
