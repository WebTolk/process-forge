# Director / Ledger / Execution Inspector Boundary Audit

Date: 2026-07-26

## Scope

Checked public and project-local surfaces that mention `supervisor`, `director`,
`agent-director`, `agent-ledger`, `lease`, `handoff`, `worker-run`, and
`process-supervisor`.

## Decision

ProcessForge keeps the existing `supervisor` files, schemas, runtime paths, and
commands for compatibility. The semantic role name is now Process Execution
Inspector. Thin CLI aliases were added:

- `execution-inspector-tick`
- `execution-inspector-run`
- `execution-inspector-status`
- `execution-inspector-stop`

These aliases call the same implementation as the existing `supervisor`
commands and do not duplicate scheduling logic.

## Boundary

Ledger records agent attendance, current presence, stale/offline state, and
leases/keys.

Director coordinates agents, process routes, handoffs, leases, returns,
finalization, and continuations. It may ask the inspector for runtime execution
state. It must not directly start shell worker processes or write worker runtime
proof files.

Execution Inspector verifies assigned task execution: ready/running/done/failed
state, worker process state, heartbeat, exit code, required outputs, expected
report, scope/overlap, and whether the task can be collected. It must not grant
leases, write the workplace agent ledger, select agents, route processes, or
accept/finalize handoffs.

Worker performs the assigned capsule task and writes the requested outputs and
runtime proof.

## Updated Surfaces

Detailed inventory is in `inventory.yaml`. The changed zones include:

- CLI help and aliases in `tools/processforge.py`.
- Process definitions for `process-supervisor` and `agent-director-supervision`.
- Supervisor/director/process-authoring prompts.
- EN/RU README, quickstart, concept, getting-started, and authoring docs.
- Supervisor profile/state display titles.
- New public boundary smoke.

## Validation Status

Initial targeted check passed:

- `python tools/smoke_director_inspector_boundary.py`

Full release and archive evidence is recorded in
`.pf/artifacts/director-inspector-boundary-report.md`.
