#!/usr/bin/env python3
"""Regression proof for Codex SessionStart lifecycle event identity."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

from pf_runtime.codex_hooks import native_envelope, normalized_event, runtime_bootstrap


ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "tools" / "processforge.py"


def pf(*args: str) -> None:
    result = subprocess.run(
        [sys.executable, str(CLI), *args],
        cwd=ROOT,
        text=True,
        capture_output=True,
        timeout=120,
    )
    if result.returncode != 0:
        raise AssertionError("command failed: " + " ".join(args) + "\n" + result.stdout + result.stderr)


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="pf-codex-lifecycle-") as directory:
        root = Path(directory)
        workplace = root / "workplace"
        project = root / "project"
        project.mkdir()
        (project / "README.md").write_text("# lifecycle identity smoke\n", encoding="utf-8")
        pf("workplace-init", "--workplace", str(workplace), "--apply")
        pf(
            "project-onboard",
            "--project-root",
            str(project),
            "--workplace",
            str(workplace),
            "--type",
            "generic-software-project",
            "--apply",
        )

        common = {
            "hook_event_name": "SessionStart",
            "cwd": str(project),
            "session_id": "lifecycle-session",
        }
        startup = {**common, "source": "startup"}
        resume = {**common, "source": "resume"}
        startup_event = normalized_event(startup)
        resume_event = normalized_event(resume)
        assert startup_event and resume_event
        assert startup_event["event_type"] == "agent.session.started"
        assert resume_event["event_type"] == "agent.session.resumed"
        assert startup_event["event_id"] != resume_event["event_id"]

        tool = {
            "hook_event_name": "PostToolUse",
            "cwd": str(project),
            "session_id": "lifecycle-session",
            "turn_id": "turn-1",
            "tool_name": "Bash",
            "tool_use_id": "tool-1",
        }
        tool_event = normalized_event(tool)
        assert tool_event and tool_event["event_type"] == "agent.command.completed"
        assert tool_event["event_id"] == "codex:PostToolUse:lifecycle-session:turn-1:tool-1"

        runtime = runtime_bootstrap()
        results = [
            runtime.host.ingest_event(native_envelope(payload), workplace, runtime.core)
            for payload in (startup, resume, resume)
        ]
        assert all(result.get("accepted") for result in results), results
        assert not results[0]["deduplicated"]
        assert not results[1]["deduplicated"]
        assert results[2]["deduplicated"]

        events_path, _ = runtime.core.event_runtime_paths(project)
        events = [
            json.loads(line)
            for line in events_path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        lifecycle = [
            event
            for event in events
            if event.get("event_type") in {"agent.session.started", "agent.session.resumed"}
            and event.get("session", {}).get("id") == "lifecycle-session"
        ]
        assert [event["event_type"] for event in lifecycle] == [
            "agent.session.started",
            "agent.session.resumed",
        ], lifecycle
        assert len({event["event_id"] for event in lifecycle}) == 2

    print("PASS: Codex lifecycle event identity smoke")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
