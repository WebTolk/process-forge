# Targeted audit: verification-state and current-work-state

## Scope and evidence boundary

This audit covers the master prompt `process-forge-verification-current-work-state-detailed-master-prompt.md`.
It is based on live repository files, the completed PF shell-worker inventory
`authoritative-facts-inventory.md`, direct source inspection, and the command
results recorded below. Prose reports are not used as verification facts.

The audit does not redesign Runtime, Agent Ledger, platform resolution, or
write MCP.

## Current confirmed state

- The existing declaration-driven projector is
  `required-output-readiness` for `process-supervisor:collect`.
- `tools/pf_runtime/host.py` builds
  `.pf/artifacts/projections/stage-obligations.json` and fingerprints the
  assignment, inspector state, required-output digests, process/stage
  declaration, and obligation for that projector.
- Its current dispatch is single-purpose: it filters obligations whose
  `projector` is exactly `required-output-readiness`; the process schema enum
  permits only that value.
- `pf.work_state` exposes the raw stage-obligations projection, but not a
  compact project-level answer with verification, semantic obligations, and
  blockers.
- A `task-doctor` command emits durable `task.doctor.passed` or
  `task.doctor.failed` events; `run-doctor` likewise emits durable
  `run.doctor.passed` or `run.doctor.failed` events. This is a usable existing
  machine-readable verification channel when a stage explicitly declares that
  doctor.
- A worker's `exit.json` is a durable completion fact. It is not, on its own,
  proof that any verification obligation passed.

## Authoritative-fact inventory

| Source | Classification | Permitted use in this slice |
| --- | --- | --- |
| Process/stage declaration and technical obligation | authoritative | Declares the projector, verification operation, gate, and relevant evidence. |
| Assignment YAML and required-output file digests | authoritative | Identifies task, declared outputs, and relevant input/output state. |
| Inspector-normalized worker `status.json`, `command.json`, `exit.json` | authoritative | Establishes worker lifecycle and the declared operation identity, not test success by itself. |
| Durable `task.doctor.*` / `run.doctor.*` journal event | authoritative | Establishes result of the explicitly declared doctor operation. |
| `stage-obligations.json`, command history, runtime state/cache | derived | Read model/cache only; rebuildable from the sources above. |
| Audit, design, review, handoff, implementation report | semantic | May be shown as semantic-obligation presence; never rewritten by a projector. |
| stdout/stderr, console PASS text, model claims, heartbeat | diagnostic or insufficient | Troubleshooting only; never creates a verification PASS. |

## Existing verification semantics and selected target

There are many semantic review/doctor gates in core process definitions. The
only existing technical-obligation implementation is the real,
already-exercised `process-supervisor:collect` stage. It is therefore the
correct bounded target; introducing a parallel arbitrary stage would be a
demonstration-only design.

The first verification operation will be an explicitly declared `task-doctor`
for that stage. Its durable PF event, keyed to the task and operation, is the
result fact. The selected slice does **not** claim that arbitrary worker
exit-code zero or a report file proves a test passed.

## Rebuildability and freshness

`stage-obligations.json` is already reconstructed by PF Core without Runtime.
The second projector can have the same property if its row fingerprint covers:

1. technical-obligation declaration;
2. selected verification operation declaration;
3. assignment fingerprint;
4. required-output digests relevant to the operation; and
5. the durable doctor-event id/payload.

Changing a required output or assignment after a passing doctor changes that
fingerprint, so the result becomes `passed` + `stale` and remains blocking.
If a declaration cannot state relevant inputs, freshness must be `unknown`,
not falsely `current`.

## Scheduler and read-path observations

Direct source inspection found that Runtime host event ingestion and each host
tick synchronously call `rebuild_stage_obligations`; the tick currently holds
the host state lock during the project loop. `work_state_payload` reads the
stored projection but recomputes current stage rows to determine freshness.

Isolated CLI measurements on this checkout, with Runtime stopped, were:

| Operation | Elapsed |
| --- | ---: |
| `runtime-host work-state` routed by the live Ledger session | 6813.30 ms |
| `runtime-host rebuild-projections` | 6679.04 ms |
| `runtime-host tick` without inspector/director | 6702.02 ms |

These timings include Python/CLI startup and do not establish a long-lived
Runtime HTTP latency regression by themselves. They do establish that the
current implementation executes non-trivial projection work on the relevant
paths. The implementation must therefore avoid making MCP reads trigger a
full rebuild; a dirty-marker/debounce redesign is deferred unless a focused
long-lived Runtime measurement proves it necessary.

## Live worker evidence from this audit

The read-only `gpt-5.3-codex-spark` worker completed with a durable
`exit.json` (`exit_code: 0`). Before the Inspector ran, its worker state still
read `running` and `worker-run collect` correctly refused it. A real
`execution-inspector-tick` observed and collected the exit, completing the
task. This confirms the intended distinction between exit evidence and
canonical collection state for this run.

## Recommended bounded slice

- **Process/stage:** `process-supervisor:collect`.
- **Declaration:** a second `technical_obligation` with projector
  `verification-state`, an explicit `task-doctor` operation/evidence
  declaration, and a verification gate.
- **Projection shape:** extend the single generic `stage-obligations.json`
  snapshot with projector-specific rows rather than create a second source of
  truth or overwrite semantic artifacts.
- **Result model:** `passed`, `failed`, `unknown`, `not_run`; freshness
  `current`, `stale`, `missing`, `invalid` (and `unknown` only where source
  freshness cannot honestly be resolved).
- **Current work state:** a compact read model composed from assignment/run,
  active sessions, worker state, technical rows, semantic-artifact presence,
  blockers, and last relevant activity. It must retain project routing and
  never expose another project's data.
- **Doctor/gate:** `projection-doctor` fails failed/missing/stale technical
  obligations; `passed` plus `stale` is never a passing gate.
- **Tests:** current/pass, failed, missing, stale-after-input-change,
  rebuild-after-deletion, CLI-without-Runtime, restart, cross-project,
  semantic-artifact protection, broken project B, and read-path behavior.

## Out of scope / follow-ups

- `changed-files` has no authoritative historical source and remains deferred.
- The current `task-complete` waiver path cannot waive `expected_report`
  because id normalization and the validator use different spellings. It was
  observed during the cancelled first worker task, is documented in the run
  log, and is not required to implement the selected projector slice.
- `doctor-context` reports health `blocked`/freshness stale after refresh in
  this dirty checkout. It is a project-context follow-up, not evidence against
  the selected verification sources.
