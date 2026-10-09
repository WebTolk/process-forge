"""Existing I/O-free Run and Assignment start document construction."""

from __future__ import annotations

from typing import Any


class WorkStartDocumentBuilder:
    def build(self, *, objective: str, selected_process: str, now: str, run_id: str, assignment_id: str, active_specializations: list[str], pin: dict[str, Any], stage_id: str) -> tuple[dict[str, Any], dict[str, Any]]:
        run = {
            "schema_version": 1,
            "id": run_id,
            "title": objective[:80],
            "process": selected_process,
            "status": "in_progress",
            "created_at": now,
            "updated_at": now,
            "objective": objective,
            "platform": "",
            "selected_specializations": active_specializations,
            "scope": {"type": "project", "project_root": "."},
            "tasks": [{"id": assignment_id, "assignment": f".pf/assignments/{assignment_id}.yaml", "status": "in_progress", "order": 1, "blocking": True}],
            "final_artifacts": [],
            "events": {"emitted": ["run.created", "process.stage.started"]},
            "privacy": {"public_safe": True},
            "process_execution": pin,
        }
        assignment = {
            "schema_version": 1,
            "id": assignment_id,
            "title": objective[:80],
            "run_id": run_id,
            "process": selected_process,
            "status": "in_progress",
            "created_at": now,
            "updated_at": now,
            "objective": objective,
            "platform": "",
            "selected_specializations": active_specializations,
            "order": 1,
            "dependencies": {"blocked_by": [], "blocks": []},
            "iterations": [],
            "result": {"status": "pending", "summary": "", "artifacts": []},
            "execution_mode": {"kind": "implementation", "code_changes_allowed": True, "artifact_changes_allowed": True, "requires_review": True},
            "stage": stage_id,
            "stage_status": "in_progress",
            "stage_execution": {"started_at": now, "evidence": [], "notes": ""},
            "stage_history": [],
            "process_execution": {
                "process_id": pin["process_id"],
                "process_version": pin["process_version"],
                "process_fingerprint": pin["process_fingerprint"],
                "snapshot_id": pin["snapshot_id"],
                "snapshot_checksum": pin["snapshot_checksum"],
            },
        }
        return run, assignment
