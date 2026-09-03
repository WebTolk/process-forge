#!/usr/bin/env python3
"""Smoke a user-defined Process/Stage contract without a Runtime daemon."""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path
from typing import Any

import yaml

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


def load_yaml(path: Path) -> dict[str, Any]:
    value = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return value if isinstance(value, dict) else {}


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="pf-stage-contract-") as temp:
        root = Path(temp)
        workplace = root / "workplace"
        project = root / "project"
        project.mkdir()
        (project / "README.md").write_text("# Stage contract smoke\n", encoding="utf-8")
        pf("workplace-init", "--workplace", str(workplace), "--apply")
        pf("project-onboard", "--project-root", str(project), "--workplace", str(workplace), "--type", "generic-software-project", "--apply")
        answers = project / "answers.yaml"
        answers.write_text(
            """schema_version: 1
process:
  id: customer-contract-flow
  name: Customer Contract Flow
  version: 1.0.0
  status: active
  kind: project_process
  scope: project
  description: User-defined contract fixture.
evolve:
  enabled: false
  reason: Contract smoke does not produce reusable learning.
responsibility_boundaries:
  primary_agent:
    - Produces the declared artifacts.
  cli_tools:
    - Runs declared checks.
process_transitions:
  - id: customer-route
    from_process: customer-contract-flow
    to_process: receiving-flow
    mode: wait_for_result
    route_id: customer-route
roles:
  - id: author
    title: Author
    responsibility: Creates contract evidence.
stages:
  - id: contract-assembly
    title: Assemble contract
    goal: Produce the contract.
    actor: primary_agent
    required_role: author
    produced_artifacts: [contract]
    exit_gates: [contract-recorded]
    automation_bindings:
      - id: contract-output-observer
        projector: required-output-readiness
        artifact: contract
        gate: contract-recorded
        source: declared-output
  - id: evidence-check
    title: Check customer evidence
    goal: Verify the user-declared evidence.
    actor: primary_agent
    required_role: author
    required_inputs: [contract]
    required_artifacts: [contract]
    required_evidence: [customer-attestation]
    produced_artifacts: [verification-note]
    entry_gates: [contract-recorded]
    exit_gates: [evidence-accepted]
artifacts:
  - id: contract
    title: Contract
    owner_role: author
    template: artifact-template
  - id: verification-note
    title: Verification note
    owner_role: author
    template: artifact-template
evidence_definitions:
  - id: customer-attestation
    title: Customer attestation
    kind: attestation
gates:
  - id: contract-recorded
    description: Contract is recorded.
    blocking: true
    required_artifact: contract
  - id: evidence-accepted
    description: Customer evidence is accepted.
    blocking: true
    required_artifact: verification-note
""",
            encoding="utf-8",
        )
        invalid_answers = project / "invalid-evidence-answers.yaml"
        invalid_answers.write_text(answers.read_text(encoding="utf-8").replace("customer-attestation]", "missing-attestation]"), encoding="utf-8")
        pf("process-create", "--project-root", str(project), "--answers", str(invalid_answers), "--dry-run", expect=1)
        pf("process-create", "--project-root", str(project), "--answers", str(answers), "--apply")
        process = load_yaml(project / "processes" / "user" / "customer-contract-flow.yaml")
        stages = process.get("stages") if isinstance(process.get("stages"), list) else []
        if [stage.get("id") for stage in stages if isinstance(stage, dict)] != ["contract-assembly", "evidence-check"]:
            raise AssertionError("user-defined stage ids were not preserved")
        if any("gates" in stage for stage in stages if isinstance(stage, dict)):
            raise AssertionError("legacy stage gates alias leaked into materialized process")
        if not isinstance(stages[0].get("automation_bindings"), list):
            raise AssertionError("automation bindings were not materialized")
        if [item.get("id") for item in process.get("evidence_definitions", [])] != ["customer-attestation"]:
            raise AssertionError("evidence definitions were not materialized")
        pf("process-doctor", "--project-root", str(project), "--process", "customer-contract-flow", "--contract-only", "--force", expect=1)
        route_map = project / ".pf" / "process-routes.yaml"
        route_map.write_text(
            """schema_version: 1
routes:
  - id: customer-route
    from_process: customer-contract-flow
    to_process: receiving-flow
    mode: wait_for_result
""",
            encoding="utf-8",
        )
        pf("process-route-doctor", "--project-root", str(project))
        pf("process-doctor", "--project-root", str(project), "--process", "customer-contract-flow", "--contract-only", "--force")
        pf("run-create", "--project-root", str(project), "--id", "customer-contract-run", "--title", "Customer contract run", "--process", "customer-contract-flow", "--apply")
        pf("task-create", "--project-root", str(project), "--run", "customer-contract-run", "--id", "customer-evidence-task", "--title", "Customer evidence", "--process", "customer-contract-flow", "--stage", "evidence-check", "--apply")
        pf("task-start", "--project-root", str(project), "--task", "customer-evidence-task")
        state = json.loads(pf("runtime-host", "work-state", "--workplace", str(workplace), "--project-root", str(project), "--json").stdout)
        current = state["current_work_state"]
        if current["active_process"] != "customer-contract-flow" or current["active_stage"] != "evidence-check":
            raise AssertionError("work state did not use the durable assignment stage")
        if current["blockers"]:
            raise AssertionError("automation bindings must not create a second blocker list")
    print("PASS: process/stage contract normalization smoke")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
