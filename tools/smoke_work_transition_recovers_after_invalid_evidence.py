#!/usr/bin/env python3
"""A rejected evidence payload must not poison a declarative Work stage."""

from __future__ import annotations

from process_execution_smoke_support import assignment, event_types, fixture, state, transition
from smoke_garage_mode_not_promoted_by_session import call_mcp


def main() -> int:
    with fixture() as (workplace, project, started):
        rejected = call_mcp(
            workplace,
            "pf.work.transition",
            {
                "project_root": str(project),
                "outcome": "completed",
                "evidence": [{"kind": "artifact", "artifact_id": "brief", "status": "ready", "path": ".pf/runs/not-a-real-evidence-file.yaml"}],
            },
        )
        after_rejection = assignment(project, started)
        execution = after_rejection.get("stage_execution", {})
        if (
            rejected.get("action") != "transition_rejected"
            or rejected.get("reason") != "invalid_evidence"
            or after_rejection.get("stage_status") != "in_progress"
            or execution.get("blockers")
            or execution.get("blocked_at")
            or after_rejection.get("stage_history")
            or "process.stage.blocked" in event_types(project)
        ):
            raise AssertionError({"rejected": rejected, "assignment": after_rejection, "events": event_types(project)})

        recovered = transition(workplace, project, "brief", "prepare-ready")
        after_recovery = assignment(project, started)
        current = state(workplace, project)
        if (
            recovered.get("action") != "stage_transitioned"
            or recovered.get("next_stage_id") != "build"
            or after_recovery.get("stage_status") != "in_progress"
            or after_recovery.get("stage_execution", {}).get("blockers")
            or after_recovery.get("stage_execution", {}).get("blocked_at")
            or len(after_recovery.get("stage_history", [])) != 1
            or current.get("stage", {}).get("id") != "build"
            or "process.stage.transitioned" not in event_types(project)
        ):
            raise AssertionError({"recovered": recovered, "assignment": after_recovery, "state": current, "events": event_types(project)})
    print("PASS: work transition recovers after invalid evidence")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
