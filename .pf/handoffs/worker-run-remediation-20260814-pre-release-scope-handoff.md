# Handoff: pre-release-remediation-implementation-20260730 -> worker-run-remediation-20260814

Objective:
Transfer only `tools/processforge.py` and `tools/smoke_worker_run_shell.py` for
the two behaviourally confirmed worker-run fixes.

Current status:
The source assignment has remained `in_progress` since 2026-07-30 with a broad
`tools/**` ownership glob, while its stated iterations do not cover these
2026-08-14 findings. It is not an active live worker and would otherwise block
all bounded remediation through stale ownership metadata.

Input artifacts:
- `.pf/artifacts/codebase-audit-20260814/findings-validation.md`
- `.pf/artifacts/codebase-audit-20260814/remediation-plan.md`
- `.pf/reviews/codebase-audit-remediation-plan-20260814-review.md`

Files changed:
None by this handoff. Target ownership is limited to the two files above.

Files not to touch:
Every other file covered by the source assignment's historical `tools/**` glob.

Known issues:
The worktree is dirty; target workers must preserve unrelated existing hunks.

Required checks:
Capsule overlap record, final source review, generic shell smoke, driver smoke,
schema validation, compilation, and release subset.

Next recommended action:
Run the two non-overlapping target assignments; final reviewer must confirm that
the diff is limited to their explicit scopes.
