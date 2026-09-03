# Design: `verification-state` and `current-work-state`

## Chosen boundary

Extend the existing generic `stage-obligations.json` projection. It remains a
derived, replace-atomically-written artifact; `current-work-state` is a compact
read view over it and existing PF facts, not another ledger or source of truth.

The first declared target is `process-supervisor:collect`, beside the existing
`required-output-readiness` obligation.

## Declaration contract

`technical_obligations` gains projector `verification-state` and a small
declaration-owned `verification` object:

```yaml
- id: task-doctor-verification
  projector: verification-state
  artifact: stage-obligations
  gate: task-doctor-passed
  source: task-doctor-event-and-required-output-digests
  verification:
    passed_event: task.doctor.passed
    failed_event: task.doctor.failed
```

The runtime matches only values from this declaration. It contains no stage
name check and no hardcoded command-name-to-stage mapping. The process
declaration therefore owns which doctor is verification and which gate it
blocks.

## Verification row

For each active declared obligation, the generic projector registry builds one
row with at least:

```text
id, projector, task_id, run_id, process_id, stage_id, obligation_id, gate
verification.result: passed | failed | unknown | not_run
verification.event_id, verification.event_type, verification.time
freshness: current | stale | missing | invalid | unknown
source_fingerprint
```

The selected latest durable passed/failed event must have the assignment/task
identity required by the row. A worker exit, output-file presence, heartbeat,
console text, or semantic report cannot substitute for that event.

## Freshness and rebuild

The source fingerprint covers the obligation declaration, assignment content,
the declared event id/payload, and relevant required-output digests. Therefore
a changed required output makes an otherwise passed verification stale.

The stored rows also retain the small set of input file paths/digests needed
for read-time freshness checks. A read checks those rows and the event-journal
version; it does not call a full projection rebuild. Runtime scheduler and CLI
rebuild continue to use one deterministic PF Core path. A missing evidence
event is `not_run`/`missing`; no unavailable source is guessed as current.

## Generic registry and doctor

Replace the current one-projector filter with a projector registry keyed by
declaration value. Both existing and new projectors write rows into the same
snapshot. Projection doctor fails a gate-bearing technical row when its
required-output state is invalid/missing/stale or its verification state is not
`passed/current`; in particular `passed + stale` fails.

## `current-work-state` payload

`pf.work_state` retains its existing project routing and adds a compact
`current_work_state` view:

```text
project, active_sessions, active_process, active_stage, run, task, assignment,
workers, technical_obligations, semantic_obligations, blockers, freshness,
last_relevant_activity
```

Technical rows are grouped by projector. `blockers` are machine-readable
objects (`kind`, `id`, `reason`) derived from failing/stale/missing technical
rows. Existing process definitions do not declare a machine-readable semantic
obligation type, so this first slice reports an empty semantic list rather
than inventing semantic state. It must not return full event history or
workplace-wide state.

## Test plan

Extend the existing stage-projector smoke with declared `task.doctor.*` facts:
current/pass, failure, missing/not-run, stale after required-output mutation,
refresh after rerun, deletion/rebuild, and semantic-file protection. Add
cross-project and compact work-state assertions. Preserve all existing runtime
and worker lifecycle smokes. A separate live Runtime/MCP proof and independent
read-only shell-worker review follow implementation.
