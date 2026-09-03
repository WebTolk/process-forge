# Handoff: codex-main -> Runtime next-slice owner

Objective: Continue the approved PF Runtime general line after correcting the first independent review findings.

Current status: startup singleton liveness and stop-before-endpoint cases are fixed and covered by deterministic long-lived smoke scenarios.

Input artifacts: `.pf/artifacts/runtime-final-independent-review-20260814/runtime-final-independent-review.md`; `.pf/artifacts/runtime-liveness-remediation-20260814/runtime-liveness-remediation-report.md`.

Files changed: `tools/pf_runtime/service.py`, `tools/smoke_long_lived_runtime.py`.

Files not to touch: PF Core authority boundaries; do not introduce Runtime Ledger, Director, Inspector, or a second event store.

Known issues: full release checksum validation remains pre-existing inventory debt; runtime lock/PID identity is not a cryptographic identity.

Required checks: retain targeted release-test pass; use a fresh read-only review if this slice is expanded.

Next recommended action: take the next master-prompt slice, Ledger-centric context/routing migration, only after a separate assignment and baseline audit.
