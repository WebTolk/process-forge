## 2026-08-14 08:12 - codex-main

Task: Remediate independently reviewed Runtime startup and stop liveness defects.
Files changed: `tools/pf_runtime/service.py`, `tools/smoke_long_lived_runtime.py`.
Artifacts changed: `.pf/artifacts/runtime-liveness-remediation-20260814/runtime-liveness-remediation-report.md`.
Templates used: none.
Tools used: ProcessForge CLI, Python `py_compile`, runtime host and long-lived smokes, codex-exec smoke, targeted release-test, schema validator.
Decisions: preserve a live starting lock, distinguish it from a stale ready record with a dead endpoint, and terminate only the local lock-owned process if stop cannot await readiness.
Risks: lock/PID identity has the documented PID-reuse limitation; full public release remains separately blocked by pre-existing checksum inventory drift.
Next steps: request independent review of this remediation or proceed to the next master-prompt Runtime slice.
Handoff: `.pf/handoffs/runtime-liveness-remediation-20260814-handoff.md`.
