#!/usr/bin/env python3
"""Smoke handoff required_specializations route to supporting agents."""

from __future__ import annotations

import tempfile
from pathlib import Path

from specialization_smoke_helpers import require_ok, run_pf, write_project, write_workspace, write_yaml


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="pf-spec-handoff-") as tmp:
        root = Path(tmp)
        workplace = write_workspace(root)
        project = write_project(root, workplace)
        write_yaml(project / ".pf" / "process-routes.yaml", {"schema_version": 1, "routes": [{"id": "fixture-route", "from_process": "source", "to_process": "target", "mode": "wait_for_result", "required_specializations": ["fixture.specialization.dev"], "requires_agent": {"role": "worker"}, "input_contract": {"required_artifacts": []}, "output_contract": {"expected_artifacts": []}}]})
        require_ok(run_pf("agent-checkin", "--workplace", str(workplace), "--agent", "agent-a", "--project-root", str(project), "--role", "worker", "--supports-specialization", "fixture.specialization.dev"))
        require_ok(run_pf("handoff-create", "--project-root", str(project), "--route", "fixture-route", "--from-run", "run-a", "--apply"))
        status = require_ok(run_pf("handoff-status", "--project-root", str(project), "--handoff", "handoff-fixture-route", "--workplace", str(workplace)))
        if "agent-a" not in status:
            raise AssertionError(status)
    print("PASS: smoke_specialization_handoff_routing")


if __name__ == "__main__":
    main()
