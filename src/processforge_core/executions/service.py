"""Pure lifecycle policy over exact attempt facts; no process or filesystem I/O."""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime

from .model import ExecutionError, ExecutionObservation, ExecutionRecord
from .ports import ExecutionRepository
from .projection import canonical_json, compatibility_payload, with_projection


def apply_evidence(
    record: ExecutionRecord, observation: ExecutionObservation
) -> ExecutionRecord:
    """Interpret already authenticated evidence, preserving uncertain ownership.

    Receipt/path/checksum authentication and proof of owned-tree absence precede
    this call. An exit alone does not establish physical inactivity. No elapsed
    time, heartbeat age or signal result retires an execution.
    """
    if observation.key != record.key or observation.launch_token != record.launch_token:
        raise ExecutionError("execution_identity_conflict")
    if record.phase == "prepared":
        raise ExecutionError("execution_activity_unknown")
    if record.process is not None and observation.process != record.process:
        raise ExecutionError("execution_identity_conflict")
    payload = compatibility_payload(record.payload_json, record.key)
    process = record.process or observation.process
    phase = record.phase
    outcome = record.outcome
    kind = observation.receipt_kind
    if kind == "spawn_failed":
        if (
            record.process is not None
            or record.phase != "starting"
            or not observation.tree_absent
        ):
            raise ExecutionError("execution_activity_unknown")
        phase, outcome = "absent", "failed"
        payload.update(
            finished_at=observation.observed_at, failure_reason="spawn failed"
        )
    elif kind in {"process", "heartbeat"}:
        if process is None:
            raise ExecutionError("execution_activity_unknown")
        if record.phase == "absent" and record.process is None:
            raise ExecutionError("execution_identity_conflict")
        if record.phase != "absent":
            phase = (
                "stopping"
                if record.phase == "stopping" or payload["status"] == "cancelled"
                else "running"
            )
            payload["pid"] = process.pid
            if payload["started_at"] is None:
                payload["started_at"] = observation.observed_at
        if kind == "heartbeat":
            previous = payload["last_heartbeat_at"]
            if previous is None or datetime.fromisoformat(
                str(previous).replace("Z", "+00:00")
            ) < datetime.fromisoformat(observation.observed_at.replace("Z", "+00:00")):
                payload["last_heartbeat_at"] = observation.observed_at
    elif kind in {"exit", "absence"}:
        if process is None:
            raise ExecutionError("execution_activity_unknown")
        if kind == "exit" and observation.exit_code is not None:
            previous_code = payload["exit_code"]
            if previous_code is not None and previous_code != observation.exit_code:
                raise ExecutionError("receipt_conflict")
            payload["exit_code"] = observation.exit_code
        if observation.tree_absent:
            phase = "absent"
            if outcome is None or (
                outcome == "unknown_exit"
                and kind == "exit"
                and observation.exit_code is not None
            ):
                if payload["exit_code"] is None:
                    outcome = "unknown_exit"
                elif observation.status in {"timed_out", "cancelled"}:
                    outcome = observation.status
                elif payload["status"] == "cancelled":
                    outcome = "cancelled"
                else:
                    outcome = "completed" if payload["exit_code"] == 0 else "failed"
                if payload["finished_at"] is None:
                    payload["finished_at"] = observation.observed_at
        elif record.phase != "absent":
            phase = "unresolved"
    # The repository assigns the first history sequence in its transaction.
    changed = replace(
        record,
        process=process,
        phase=phase,
        outcome=outcome,
        history_seq=(record.history_seq or 1) if phase == "absent" else None,
        payload_json=canonical_json(payload),
    )
    return with_projection(changed)


class ExecutionService:
    """Expose lifecycle interpretation and DTO production without OS composition."""

    def __init__(self, repository: ExecutionRepository) -> None:
        self.repository = repository

    def observe(
        self,
        observation: ExecutionObservation,
        *,
        expected_revision: int,
        generation: int,
    ) -> ExecutionRecord:
        """Apply validated exact-attempt evidence through repository CAS."""
        return self.repository.apply_observation(
            observation, expected_revision=expected_revision, generation=generation
        )

    def payload(self, record: ExecutionRecord) -> dict[str, object]:
        """Produce the existing public status DTO without storage bookkeeping."""
        from .projection import projected_payload

        return projected_payload(record)
