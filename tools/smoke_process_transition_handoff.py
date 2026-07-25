#!/usr/bin/env python3
"""Smoke test for process routes and formal handoff packages."""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

from processforge_subprocess import CommandResult, diagnostic_text, run_command as run_processforge_command


ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "tools" / "processforge.py"


def pf(*args: str, expect: int = 0, timeout: int = 90) -> CommandResult:
    result = run_processforge_command([sys.executable, str(CLI), *args], cwd=ROOT, timeout=timeout)
    if result.timed_out:
        raise AssertionError("timeout: " + " ".join(args) + "\n" + diagnostic_text(result))
    if result.returncode != expect:
        raise AssertionError(f"expected {expect}, got {result.returncode}: {' '.join(args)}\n{diagnostic_text(result)}")
    return result


def make_project(root: Path) -> tuple[Path, Path]:
    workplace = root / "workplace"
    project = root / "project"
    project.mkdir()
    (project / "README.md").write_text("# Handoff smoke\n", encoding="utf-8")
    pf("workplace-init", "--workplace", str(workplace), "--apply")
    pf("project-onboard", "--project-root", str(project), "--workplace", str(workplace), "--type", "generic-software-project", "--apply")
    return workplace, project


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="pf-handoff-") as temp:
        workplace, project = make_project(Path(temp))
        (project / ".pf" / "process-routes.yaml").write_text(
            """schema_version: 1
routes:
  - id: process-a-to-process-b
    from_process: process-a
    to_process: process-b
    mode: wait_for_result
    requires_agent:
      role: decomposer
      status: checked_in
    input_contract:
      required_artifacts:
        - .pf/artifacts/input.md
    output_contract:
      expected_artifacts:
        - .pf/artifacts/output.md
    return:
      to_process: process-a
      to_stage: review
      continue_run: true
""",
            encoding="utf-8",
        )
        pf("process-route-validate", "--project-root", str(project))
        pf("handoff-create", "--project-root", str(project), "--route", "process-a-to-process-b", "--from-run", "run-a", "--id", "handoff-a-b", "--apply")
        waiting = json.loads(pf("handoff-status", "--project-root", str(project), "--handoff", "handoff-a-b", "--json").stdout)
        if waiting["status"] != "waiting_for_agent":
            raise AssertionError("handoff should wait before target agent checkin")
        pf("agent-checkin", "--workplace", str(workplace), "--agent", "decomposer-local", "--session", "sess-decomposer-001", "--role", "decomposer")
        ready = json.loads(pf("handoff-status", "--project-root", str(project), "--handoff", "handoff-a-b", "--workplace", str(workplace), "--json").stdout)
        if ready["status"] != "ready":
            raise AssertionError("handoff did not become ready with target role online")
        pf("handoff-accept", "--project-root", str(project), "--handoff", "handoff-a-b", "--agent", "decomposer-local", "--session", "sess-decomposer-001")
        output = project / ".pf" / "artifacts" / "output.md"
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text("# Output\n", encoding="utf-8")
        pf("handoff-return", "--project-root", str(project), "--handoff", "handoff-a-b", "--artifact", ".pf/artifacts/output.md")
        pf("handoff-finalize", "--project-root", str(project), "--handoff", "handoff-a-b")
        pf("handoff-doctor", "--project-root", str(project))
    print("PASS: process transition handoff smoke")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
