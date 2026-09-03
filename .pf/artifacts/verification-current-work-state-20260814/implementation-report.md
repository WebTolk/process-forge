# Implementation report: verification-state and current-work-state

## Result

Implemented the bounded second declaration-driven projector and compact work
state described in the approved audit/design.

## Changed contract

- `process-supervisor:collect` now declares `task-doctor-verification` beside
  `required-output-readiness`.
- The declaration supplies `passed_event` and `failed_event`; Runtime matches
  these values from the declaration and contains no stage-name special case.
- Process schema allows `verification-state` plus the narrow verification
  event contract.

## Projection and freshness

- `stage-obligations.json` remains the only technical projection artifact.
- Its generic registry now builds both existing readiness and verification
  rows.
- Verification PASS/FAIL comes only from a task-matching durable
  `task.doctor.*` event.
- Fingerprints include declaration, assignment, required-output digests, and
  the selected event. A changed output makes a passed verification stale.
- Projection doctor rejects failed/not-run verification and stale/missing
  projection rows; `passed + stale` cannot pass.

## Read model and safety

`pf.work_state` now includes `current_work_state` with active project/session
context, technical obligations, empty-by-honesty semantic obligations,
machine-readable blockers, freshness, and last relevant activity. It keeps
Ledger project routing and does not create a new ledger, event store, or write
MCP surface. Projectors still write only the technical JSON artifact and do
not touch semantic files.

## Focused verification

- `python -m py_compile tools/pf_runtime/host.py tools/smoke_stage_projectors.py tools/smoke_verification_current_work_state.py` — PASS.
- `python tools/validate-process-forge-schemas.py --root .` — PASS.
- `python tools/smoke_stage_projectors.py` — PASS.
- `python tools/smoke_verification_current_work_state.py` — PASS (not-run,
  pass/current, stale, refresh, failure event, semantic protection and compact
  work-state blockers).
- `git diff --check` — PASS.

## Remediation review

The initial independent review identified H1 (rebuild-stable freshness) and
M1 (a full rescan on the read path). The implementation now includes the
task verification fingerprint in doctor events and uses per-row read-model
freshness checks. The separate Spark remediation review marks both findings
PASS in `.pf/reviews/verification-current-work-state-20260814-remediation-review.md`.

## Known boundaries

- The root checkout's `projection-doctor` remains FAIL because an unrelated
  pre-existing `runtime-readonly-review` task has a missing required output;
  focused isolated projections pass.
- Long-lived Runtime restart/MCP proof and independent shell-worker review are
  still pending in this run.
- The legacy pre-release task's broad ownership prevented a `codex-exec`
  implementation worker despite the documented forced handoff. The primary
  coordinator performed this tightly coupled slice; the failed worker launch
  is recorded as `iter-001`.
