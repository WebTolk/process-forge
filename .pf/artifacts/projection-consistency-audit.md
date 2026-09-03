# Projection Consistency Audit

Status: partial

Current implementation:

- Agent check-in, heartbeat, and checkout write current-session refs.
- `session_read.session_context_payload()` reads presence, obligations, context
  freshness, execution readiness, and search status for the Ledger-bound
  session.
- `runtime-host rebuild-projections` refreshes stage obligations in the broad
  project-init acceptance smoke.

Validated:

- `python tools/smoke_project_init_acceptance.py` confirmed stage obligation
  projection changes from `architecture-plan` to `implementation`.

Residual: stale presence/current-session projection consistency after session
expiry was not changed in this slice.
