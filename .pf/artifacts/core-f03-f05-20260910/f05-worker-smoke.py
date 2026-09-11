#!/usr/bin/env python3
"""Portable smoke for durable terminal completion recovery.

The fixture uses a temporary ProcessForge project and injects one failure into
the ordinary service path.  A fresh service instance then retries through the
same transition API, proving that the run-scoped intent is sufficient to
finish the terminal projection without revalidating a different outcome.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import yaml

import processforge as core
from processforge_core.process_execution import ProcessExecutionService
from process_execution_smoke_support import assignment, fixture, run, transition


def require(condition: bool, payload: object) -> None:
    if not condition:
        raise AssertionError(payload)


def test_recovery_after_summary_write_failure() -> None:
    with fixture() as (workplace, project, started):
        require(transition(workplace, project, "brief", "prepare-ready").get("next_stage_id") == "build", "prepare")
        require(transition(workplace, project, "change", "build-ready").get("next_stage_id") == "verify", "build")

        service = ProcessExecutionService(project, workplace, core)
        summary_path = project / ".pf" / "runs" / str(started["run_id"]) / "summary.md"
        original_atomic_text = ProcessExecutionService._atomic_text
        injected = {"done": False}

        def fail_once(owner: ProcessExecutionService, path: Path, content: str) -> None:
            if path == summary_path and not injected["done"]:
                injected["done"] = True
                raise OSError("one-shot summary failure")
            original_atomic_text(owner, path, content)

        try:
            with patch.object(ProcessExecutionService, "_atomic_text", fail_once):
                service.transition(
                    outcome="completed",
                    evidence=[
                        {"kind": "artifact", "artifact_id": "report", "status": "ready"},
                        {"kind": "gate", "gate_id": "verify-ready", "status": "passed"},
                    ],
                    notes="original completion note",
                )
        except OSError as exc:
            require(str(exc) == "one-shot summary failure", exc)
        else:
            raise AssertionError("fault injection did not interrupt completion")

        journal = project / ".pf" / "runs" / str(started["run_id"]) / "completion-intent.yaml"
        require(journal.is_file(), "completion intent was not retained after failure")
        recovered = ProcessExecutionService(project, workplace, core).transition(
            outcome="different-outcome-is-ignored",
            evidence=None,
            notes="different retry note is ignored",
        )
        require(recovered.get("action") == "run_completed", recovered)
        require(not journal.exists(), "completion intent was not removed after convergence")
        require(run(project, started).get("status") == "completed", run(project, started))
        final_assignment = assignment(project, started)
        require(final_assignment.get("status") == "done", final_assignment)
        require(len(final_assignment.get("stage_history", [])) == 1, final_assignment)
        require(final_assignment.get("result", {}).get("summary") == "original completion note", final_assignment)

        repeated = ProcessExecutionService(project, workplace, core).transition(outcome="completed")
        require(repeated.get("reason") == "work_is_terminal", repeated)


def test_mismatched_intent_fails_closed() -> None:
    with fixture() as (workplace, project, started):
        run_dir = project / ".pf" / "runs" / str(started["run_id"])
        journal = run_dir / "completion-intent.yaml"
        journal.write_text(yaml.safe_dump({"kind": "pf.process.completion-intent", "run_id": "other", "assignment_id": started["assignment_id"]}), encoding="utf-8")
        result = ProcessExecutionService(project, workplace, core).transition(outcome="completed")
        require(result.get("reason") == "completion_intent_invalid", result)
        require(run(project, started).get("status") == "in_progress", run(project, started))


def main() -> int:
    test_recovery_after_summary_write_failure()
    test_mismatched_intent_fails_closed()
    print("PASS: recoverable terminal completion")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
