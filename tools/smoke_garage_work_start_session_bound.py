#!/usr/bin/env python3
"""Smoke test for session-bound pf.work.start telemetry linkage."""

from smoke_garage_mode_not_promoted_by_session import call_mcp, cli

import tempfile
from pathlib import Path

import yaml


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="pf-work-start-session-") as raw:
        root = Path(raw)
        workplace = root / "workplace"
        project = root / "project"
        cli("workplace-init", "--workplace", str(workplace), "--apply")
        cli("project-onboard", "--project-root", str(project), "--workplace", str(workplace), "--type", "generic", "--apply")
        cli("agent-checkin", "--workplace", str(workplace), "--agent", "fixture-agent", "--session", "fixture-session", "--project-root", str(project))
        payload = call_mcp(workplace, "pf.work.start", {"project_root": str(project), "session_id": "fixture-session", "objective": "Check session assets"})
        if payload.get("action") != "created_new" or payload.get("session", {}).get("status") != "bound":
            raise AssertionError(payload)
        task = yaml.safe_load((project / ".pf" / "assignments" / f"{payload['assignment_id']}.yaml").read_text(encoding="utf-8"))
        if task.get("session", {}).get("id") != "fixture-session":
            raise AssertionError(task)
    print("PASS: session-bound pf.work.start records telemetry linkage")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
