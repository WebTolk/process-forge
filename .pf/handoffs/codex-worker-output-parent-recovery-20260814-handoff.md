# Handoff: codex-main -> runtime-liveness-remediation

Objective: Fix the two independently confirmed Runtime liveness findings.

Current status: Codex worker transport now uses UTF-8, emits report-only final output, and creates the expected output directory. The final review output is preserved as a durable artifact.

Input artifacts: `.pf/artifacts/runtime-final-independent-review-20260814/runtime-final-independent-review.md`; `.pf/artifacts/codex-worker-output-parent-recovery-20260814/output-parent-recovery-report.md`.

Files changed: `tools/codex_exec_worker.py`, `tools/smoke_codex_exec_worker.py`.

Files not to touch: PF Core business logic is out of scope; retain the recovered reviewer artifact unchanged.

Known issues: `runtime-final-independent-review` worker state is failed only because its original output parent did not exist; its actual process exit code is zero and review stdout is preserved.

Required checks: test simultaneous `runtime start` and `runtime stop` during an endpoint-unpublished live state; retain stale-dead-PID recovery.

Next recommended action: implement the narrow liveness remediation in `tools/pf_runtime/service.py` and `tools/smoke_long_lived_runtime.py`.
