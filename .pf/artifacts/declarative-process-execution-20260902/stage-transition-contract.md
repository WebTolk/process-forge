# Stage Transition Contract

Status: ready_for_review
Date: 2026-09-02

## Request

```yaml
outcome: completed
evidence:
  - kind: artifact
    artifact_id: scope
    status: ready
    path: .pf/artifacts/scope.md
  - kind: gate
    gate_id: scope-accepted
    status: passed
    summary: Scope accepted by the responsible agent.
notes: Optional transition note.
```

The caller never supplies `next_stage`. Linear order or the selected outcome's
`next_stage` declaration determines routing.

## Result

Successful non-final transition returns `action: stage_transitioned` with the
previous and next stages. Successful final transition returns
`action: run_completed` and completes Assignment and Run in the same mutation.

Blocked transition returns `action: blocked` with machine-readable blockers.
Blocker codes include `required_input_missing`, `artifact_evidence_missing`,
`artifact_path_missing`, `gate_evidence_missing`, `automation_not_ready`,
`outcome_not_allowed`, `process_not_pinned`, and `run_completion_blocked`.

## Events

The service emits:

- `process.stage.started`
- `process.stage.completed`
- `process.stage.blocked`
- `process.stage.transitioned`

Each event includes Run id, Assignment id, Process id/version, current stage,
previous stage, next stage, timestamp through the envelope, and outcome.
The existing event journal and dispatch path are reused.
