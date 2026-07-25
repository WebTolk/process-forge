#!/usr/bin/env python3
"""Smoke test for Agent Director tick scheduling and stale lease marking."""

from __future__ import annotations

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


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="pf-director-") as temp:
        root = Path(temp)
        workplace = root / "workplace"
        project = root / "project"
        project.mkdir()
        (project / "README.md").write_text("# Director smoke\n", encoding="utf-8")
        pf("workplace-init", "--workplace", str(workplace), "--apply")
        pf("project-onboard", "--project-root", str(project), "--workplace", str(workplace), "--type", "generic-software-project", "--apply")
        (project / ".pf" / "process-routes.yaml").write_text(
            """schema_version: 1
routes:
  - id: feature-to-decomposition
    from_process: feature-development
    to_process: task-decomposition
    mode: wait_for_result
    requires_agent:
      role: decomposer
      status: checked_in
    input_contract:
      required_artifacts: []
    output_contract:
      expected_artifacts: []
    return:
      to_process: feature-development
      to_stage: planning-review
      continue_run: true
""",
            encoding="utf-8",
        )
        pf("handoff-create", "--project-root", str(project), "--route", "feature-to-decomposition", "--from-run", "feature-run", "--id", "handoff-feature", "--apply")
        pf("agent-director-tick", "--workplace", str(workplace), "--project-root", str(project))
        handoff = (project / ".pf" / "handoffs" / "handoff-feature" / "handoff.yaml").read_text(encoding="utf-8")
        if "status: waiting_for_agent" not in handoff:
            raise AssertionError("director should keep handoff waiting without available agent")
        pf("agent-checkin", "--workplace", str(workplace), "--agent", "decomposer-local", "--session", "sess-decomposer-001", "--role", "decomposer")
        pf("agent-director-tick", "--workplace", str(workplace), "--project-root", str(project))
        handoff = (project / ".pf" / "handoffs" / "handoff-feature" / "handoff.yaml").read_text(encoding="utf-8")
        if "status: ready" not in handoff or "lease-handoff-feature-decomposer-local" not in handoff:
            raise AssertionError("director did not grant lease and mark handoff ready")
        pf("agent-lease-grant", "--workplace", str(workplace), "--id", "lease-expired", "--agent", "decomposer-local", "--session", "sess-decomposer-001", "--ttl", "-1")
        pf("agent-director-tick", "--workplace", str(workplace), "--project-root", str(project))
        lease = (workplace / "runtime" / "agent-leases" / "lease-expired.yaml").read_text(encoding="utf-8")
        if "status: stale" not in lease:
            raise AssertionError("director did not mark expired lease stale")
    print("PASS: agent director tick smoke")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
