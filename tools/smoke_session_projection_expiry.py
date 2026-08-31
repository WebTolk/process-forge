#!/usr/bin/env python3
"""Smoke test for stale Ledger presence updating current-session projections."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import processforge as core


PF = ROOT / "tools" / "processforge.py"


def cli(*args: str) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        [sys.executable, str(PF), *args],
        cwd=ROOT,
        text=True,
        encoding="utf-8",
        errors="strict",
        capture_output=True,
        timeout=120,
    )
    if result.returncode != 0:
        raise AssertionError(result.stdout + result.stderr)
    return result


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="pf-session-expiry-") as raw:
        root = Path(raw)
        workplace = root / "workplace"
        project = root / "project"
        cli("workplace-init", "--workplace", str(workplace), "--apply")
        cli("project-onboard", "--project-root", str(project), "--workplace", str(workplace), "--type", "generic", "--apply")
        cli(
            "agent-checkin",
            "--workplace",
            str(workplace),
            "--agent",
            "fixture-agent",
            "--session",
            "fixture-session",
            "--project-root",
            str(project),
            "--ttl",
            "1",
        )
        current_path = project / ".pf" / "runtime" / "current-session.json"
        current = json.loads(current_path.read_text(encoding="utf-8"))
        if current.get("status") != "online":
            raise AssertionError(current)

        presence_path = core.agent_presence_path(workplace, "fixture-agent", "fixture-session")
        presence = json.loads(presence_path.read_text(encoding="utf-8"))
        presence["last_seen_at"] = "2000-01-01T00:00:00Z"
        presence_path.write_text(json.dumps(presence, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")

        core.update_stale_agent_presence(workplace)
        stale_current = json.loads(current_path.read_text(encoding="utf-8"))
        if stale_current.get("status") != "stale":
            raise AssertionError(stale_current)
        workspace_current = json.loads(core.workplace_current_session_path(workplace, core.project_id(project)).read_text(encoding="utf-8"))
        if workspace_current.get("status") != "stale":
            raise AssertionError(workspace_current)
    print("PASS: stale session expiry updates current-session projections")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
