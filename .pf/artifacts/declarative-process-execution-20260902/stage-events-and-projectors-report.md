# Stage Events And Projectors Report

Date: 2026-09-02

## Canonical State

`Run.process_execution` pins the complete Process definition, fingerprint, context snapshot and capsule checksum. `Assignment.stage`, `stage_status`, `stage_execution` and `stage_history` are the durable execution state. The schemas now describe these fields rather than relying on unrestricted additional properties.

## Events

The transition service emits `process.stage.started`, `process.stage.completed`, `process.stage.blocked` and `process.stage.transitioned`. The event schema requires the run, assignment, process, stage, previous/next stage, outcome and blockers fields for these event types.

## Projection

`process-execution-state.json` is refreshed after start and every transition. Runtime `work_state` uses the pinned declarative state for its stage contract and automation obligations, so it no longer overlays the current live Process YAML over a pinned Run.

## Evidence

`smoke_work_transition_emits_stage_events.py`, `smoke_stage_projectors.py` and `smoke_process_stage_contract_normalization.py` passed after the final changes.
