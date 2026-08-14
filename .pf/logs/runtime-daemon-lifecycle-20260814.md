## 2026-08-14 08:25 - codex-main

Task: Audit and redesign the long-lived Runtime daemon lifecycle.
Files changed: `tools/pf_runtime/service.py`, `tools/smoke_long_lived_runtime.py`.
Artifacts changed: `daemon-lifecycle-audit.md`, `daemon-lifecycle-implementation-report.md`.
Templates used: none.
Tools used: shell fallback repository analysis (Serena unavailable), ProcessForge CLI, Python py_compile, Runtime smokes, targeted release-test, schema validator.
Decisions: replace overlapping liveness heuristics with one instance-id-based lifecycle inspection; let only the child daemon own its matching lock.
Risks: OS PID plus a local random instance ID is robust against ordinary stale/PID-reuse records, but not a security boundary against a malicious local writer.
Next steps: independent read-only review of lifecycle transitions and retained stale-recovery behaviour.
Handoff: `.pf/handoffs/runtime-daemon-lifecycle-20260814-handoff.md`.

## 2026-08-14 08:29 - codex-main

Task: Address independent lifecycle-review WARN for a missing lock with a live daemon.
Files changed: `tools/pf_runtime/service.py`, `tools/smoke_long_lived_runtime.py`.
Artifacts changed: `daemon-lifecycle-orphaned-instance-report.md`.
Templates used: none.
Tools used: Python py_compile, Runtime smokes, schema validator.
Decisions: classify a live matching service identity with lost lock as orphaned; refuse duplicate start and allow stop only through verified readiness endpoint.
Risks: an orphaned instance without a verified endpoint intentionally requires explicit operator recovery rather than unsafe PID termination.
Next steps: complete the lifecycle run and proceed only to the next master-prompt slice.
Handoff: `.pf/handoffs/runtime-daemon-lifecycle-20260814-handoff.md`.
