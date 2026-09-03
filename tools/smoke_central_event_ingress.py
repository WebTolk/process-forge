#!/usr/bin/env python3
"""End-to-end proof for the first raw-first Central Event Ingress slice."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

from processforge_subprocess import diagnostic_text, run_command
from pf_runtime.codex_hooks import normalized_event


ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "tools" / "processforge.py"


def pf(*args: str, expect: int = 0) -> str:
    result = run_command([sys.executable, str(CLI), *args], cwd=ROOT, timeout=120)
    if result.returncode != expect:
        raise AssertionError(f"expected {expect}: {' '.join(args)}\n{diagnostic_text(result)}")
    return result.stdout if expect == 0 else result.stdout + result.stderr


def save(path: Path, payload: dict[str, object]) -> Path:
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return path


def native_event(project: Path, session: str, hook: str, payload: dict[str, object], derived: dict[str, object] | None) -> dict[str, object]:
    return {
        "provider": "codex",
        "adapter": "codex-hooks",
        "native_event_type": hook,
        "native_event_id": None,
        "native_id_scope": "session",
        "native_event_id_stable": False,
        "source_session_id": session,
        "source_project_ref": str(project),
        "payload_version": "codex-hooks.v1",
        "raw_payload": payload,
        "derived_event": derived,
    }


def derived(project: Path, session: str, event_type: str, event_id: str) -> dict[str, object]:
    return {
        "schema_version": 1,
        "event_type": event_type,
        "event_id": event_id,
        "project_root": str(project),
        "session_id": session,
        "agent_id": "codex",
        "source": {"adapter": "codex-hooks", "agent": "codex", "session_id": session},
    }


def existing_runtime_event_id(event_id: str) -> str:
    """The normalized Host has historically wrapped non-evt IDs this way."""

    return "evt_" + hashlib.sha256(event_id.encode("utf-8")).hexdigest()[:32]


def raw_records(workplace: Path) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for shard in (workplace / "runtime" / "agent-events" / "raw" / "v1").rglob("*.ndjson"):
        rows.extend(json.loads(line) for line in shard.read_text(encoding="utf-8").splitlines() if line)
    return rows


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="pf-central-ingress-") as directory:
        root = Path(directory)
        workplace = root / "workplace"
        first, second = root / "first", root / "second"
        first.mkdir()
        second.mkdir()
        (first / "README.md").write_text("# first\n", encoding="utf-8")
        (second / "README.md").write_text("# second\n", encoding="utf-8")
        pf("workplace-init", "--workplace", str(workplace), "--apply")
        pf("project-onboard", "--project-root", str(first), "--workplace", str(workplace), "--type", "generic-software-project", "--apply")
        pf("project-onboard", "--project-root", str(second), "--workplace", str(workplace), "--type", "generic-software-project", "--apply")

        session = "central-session"
        start = native_event(
            first,
            session,
            "SessionStart",
            {"hook_event_name": "SessionStart", "source": "startup", "cwd": str(first), "session_id": session},
            derived(first, session, "agent.session.started", "codex:SessionStart:central-session::"),
        )
        started = json.loads(pf("runtime-host", "event", "--workplace", str(workplace), "--input", str(save(root / "start.json", start)), "--json"))
        assert started["accepted"] and started["event_id"] == existing_runtime_event_id("codex:SessionStart:central-session::"), started

        tool = native_event(
            first,
            session,
            "PostToolUse",
            {"hook_event_name": "PostToolUse", "cwd": str(first), "session_id": session, "turn_id": "turn-1", "tool_name": "Bash", "tool_use_id": "tool-1"},
            derived(first, session, "agent.command.completed", "codex:PostToolUse:central-session:turn-1:tool-1"),
        )
        assert normalized_event(start["raw_payload"])["event_type"] == "agent.session.started"
        assert normalized_event(tool["raw_payload"])["event_type"] == "agent.command.completed"
        non_bash = {**tool["raw_payload"], "tool_name": "Read"}
        assert normalized_event(non_bash)["event_type"] == "agent.tool.completed"
        assert normalized_event({"hook_event_name": "UndocumentedHook", "cwd": str(first), "session_id": session}) is None
        tool_path = save(root / "tool.json", tool)
        fallback = json.loads(pf("runtime-host", "event", "--workplace", str(workplace), "--input", str(tool_path), "--json"))
        assert fallback["accepted"] and not fallback["deduplicated"]
        assert fallback["event_id"] == existing_runtime_event_id("codex:PostToolUse:central-session:turn-1:tool-1")
        assert len(raw_records(workplace)) == 2

        # Simulate a crash after the raw append: the raw journal stays
        # authoritative and a duplicate delivery repairs only the missing
        # project effect, without appending a second raw record.
        events_path = first / str(fallback["events"])
        remaining = [
            line for line in events_path.read_text(encoding="utf-8").splitlines()
            if json.loads(line).get("event_id") != fallback["event_id"]
        ]
        events_path.write_text("\n".join(remaining) + "\n", encoding="utf-8")
        repaired = json.loads(pf("runtime-host", "event", "--workplace", str(workplace), "--input", str(tool_path), "--json"))
        assert repaired["deduplicated"] and not repaired["duplicate"]
        assert len(raw_records(workplace)) == 2

        pf("runtime", "start", "--workplace", str(workplace), "--timeout", "10")
        try:
            daemon = json.loads(pf("runtime", "event", "--workplace", str(workplace), "--input", str(tool_path), "--json"))
            assert daemon["accepted"] and daemon["deduplicated"]
            assert daemon["raw_event_id"] == fallback["raw_event_id"]
            assert len(raw_records(workplace)) == 2
        finally:
            pf("runtime", "stop", "--workplace", str(workplace), "--timeout", "10")

        adapter_env = dict(os.environ, PF_CODEX_HOOK_DEBUG="1")
        unknown_hook = subprocess.run(
            [sys.executable, str(ROOT / "tools" / "pf_runtime" / "codex_hooks.py")],
            input=json.dumps({"hook_event_name": "UndocumentedHook", "cwd": str(first), "session_id": session, "value": "kept-raw"}),
            text=True,
            capture_output=True,
            cwd=ROOT,
            env=adapter_env,
            check=True,
        )
        assert not unknown_hook.stdout
        unknown_result = json.loads(unknown_hook.stderr)
        assert unknown_result["status"] == "delivered" and unknown_result["normalized_event_ids"] == []
        assert len(raw_records(workplace)) == 3

        mismatch = native_event(
            second,
            session,
            "PostToolUse",
            {"hook_event_name": "PostToolUse", "cwd": str(second), "session_id": session, "turn_id": "turn-x", "tool_use_id": "tool-x"},
            derived(second, session, "agent.command.completed", "codex:PostToolUse:central-session:turn-x:tool-x"),
        )
        denied = pf("runtime-host", "event", "--workplace", str(workplace), "--input", str(save(root / "mismatch.json", mismatch)), "--json", expect=1)
        assert "not authorized" in denied
        records = raw_records(workplace)
        assert len(records) == 4 and all(record.get("privacy") == "private" for record in records)
    print("PASS: central raw-first ingress smoke")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
