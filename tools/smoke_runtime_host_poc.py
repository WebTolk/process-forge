#!/usr/bin/env python3
"""Smoke test for the lazy PF Runtime host PoC."""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

from processforge_subprocess import CommandResult, diagnostic_text, run_command as run_processforge_command


ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "tools" / "processforge.py"


def pf(*args: str, expect: int = 0, timeout: int = 120) -> CommandResult:
    result = run_processforge_command([sys.executable, str(CLI), *args], cwd=ROOT, timeout=timeout)
    if result.timed_out:
        raise AssertionError("timeout: " + " ".join(args) + "\n" + diagnostic_text(result))
    if result.returncode != expect:
        raise AssertionError(f"expected {expect}, got {result.returncode}: {' '.join(args)}\n{diagnostic_text(result)}")
    return result


def make_project(root: Path, name: str, workplace: Path, mode: str) -> Path:
    project = root / name
    project.mkdir()
    (project / "README.md").write_text(f"# {name}\n", encoding="utf-8")
    pf("project-onboard", "--project-root", str(project), "--workplace", str(workplace), "--type", "generic-software-project", "--apply")
    pf("project-mode", "set", "--project-root", str(project), "--workplace", str(workplace), "--mode", mode)
    return project


def write_event(path: Path, payload: dict[str, object]) -> Path:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="pf-runtime-host-poc-") as temp:
        root = Path(temp)
        workplace = root / "workplace"
        pf("workplace-init", "--workplace", str(workplace), "--apply")
        pf("workplace-mode", "set", "--workplace", str(workplace), "--director-enabled", "true", "--director-office-enabled", "true")
        project_a = make_project(root, "project-a", workplace, "organized")
        project_b = make_project(root, "project-b", workplace, "simple")

        pf("runtime-host", "init", "--workplace", str(workplace), "--project-root", str(project_a), "--project-root", str(project_b))

        event_a = write_event(
            root / "event-a.json",
            {
                "schema_version": 1,
                "event_id": "runtime-host-a-start",
                "event_type": "agent.session.started",
                "source": {"adapter": "generic", "agent": "codex-a", "session_id": "sess-a", "role": "worker"},
                "project_root": str(project_a),
                "role": "worker",
                "payload": {"status": "started"},
            },
        )
        event_b = write_event(
            root / "event-b.json",
            {
                "schema_version": 1,
                "event_id": "runtime-host-b-start",
                "event_type": "agent.session.started",
                "source": {"adapter": "generic", "agent": "claude-b", "session_id": "sess-b", "role": "worker"},
                "project_root": str(project_b),
                "role": "worker",
                "payload": {"status": "started"},
            },
        )
        pf("runtime-host", "event", "--workplace", str(workplace), "--input", str(event_a), "--json")
        pf("runtime-host", "event", "--workplace", str(workplace), "--input", str(event_b), "--json")
        duplicate = json.loads(pf("runtime-host", "event", "--workplace", str(workplace), "--input", str(event_b), "--json").stdout)
        if duplicate["duplicate"] is not True:
            raise AssertionError("duplicate runtime event was not recognized")

        events_a = [json.loads(line) for line in (project_a / ".pf" / "runtime" / "events" / "events.ndjson").read_text(encoding="utf-8").splitlines() if line.strip()]
        events_b = [json.loads(line) for line in (project_b / ".pf" / "runtime" / "events" / "events.ndjson").read_text(encoding="utf-8").splitlines() if line.strip()]
        sessions_a = {((item.get("session") or {}).get("id") if isinstance(item, dict) else "") for item in events_a}
        sessions_b = {((item.get("session") or {}).get("id") if isinstance(item, dict) else "") for item in events_b}
        if "sess-a" not in sessions_a or "sess-b" in sessions_a:
            raise AssertionError("project A event routing mixed events")
        if "sess-b" not in sessions_b or "sess-a" in sessions_b:
            raise AssertionError("project B event routing mixed events")

        state_a = json.loads(pf("runtime-host", "project-state", "--workplace", str(workplace), "--session", "sess-a", "--json").stdout)
        state_b = json.loads(pf("runtime-host", "project-state", "--workplace", str(workplace), "--session", "sess-b", "--json").stdout)
        if state_a["project"]["project_id"] == state_b["project"]["project_id"]:
            raise AssertionError("session routing did not isolate projects")

        status = json.loads(pf("runtime-host", "status", "--workplace", str(workplace), "--project-root", str(project_a), "--project-root", str(project_b), "--json").stdout)
        if len(status["projects"]) != 2 or status["ledger_sessions"] < 1:
            raise AssertionError("runtime status did not show two projects and ledger sessions")

        tick = json.loads(pf("runtime-host", "tick", "--workplace", str(workplace), "--project-root", str(project_a), "--project-root", str(project_b), "--director", "--inspector", "--json").stdout)
        modes = {item["project_id"]: item for item in tick["projects"]}
        if not any(item["director"] == "tick" for item in modes.values()):
            raise AssertionError("runtime did not host director tick for organized project")
        if not any(item["director"] == "skipped_simple" for item in modes.values()):
            raise AssertionError("runtime did not skip director tick for simple project")

        pf("runtime-host", "rebuild-projections", "--project-root", str(project_a), "--project-root", str(project_b), "--json")
        if not (project_b / ".pf" / "artifacts" / "projections" / "command-history.md").is_file():
            raise AssertionError("projection was not rebuilt after simulated restart")

        pf("events-validate", "--project-root", str(project_a))
        pf("events-validate", "--project-root", str(project_b))
        pf("project-context-check", "--project-root", str(project_a), expect=0)

    print("PASS: runtime host PoC smoke")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
