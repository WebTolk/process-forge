# Handoff: codex-main -> shell-worker-daemon-lifecycle-review

Objective: Independently review the simplified Runtime daemon lifecycle.

Current status: lifecycle ownership is now defined by matching `instance_id`, PID and service state; targeted tests pass.

Input artifacts: `.pf/artifacts/runtime-daemon-lifecycle-20260814/daemon-lifecycle-audit.md`; `.pf/artifacts/runtime-daemon-lifecycle-20260814/daemon-lifecycle-implementation-report.md`.

Files changed: `tools/pf_runtime/service.py`, `tools/smoke_long_lived_runtime.py`.

Files not to touch: all product code and tests are read-only for this review.

Known issues: full release remains separately blocked by pre-existing checksum inventory debt; no public compatibility contract exists for this unreleased Runtime PoC.

Required checks: transition logic for ready/starting/stopping/failed/stale, ownership checks, force-stop safety and stale legacy lock recovery.

Next recommended action: return only an evidence-backed Markdown review or PASS.

## Review follow-up

The review WARN was fixed: a lockless but live `instance_id` service is now `orphaned`, cannot be duplicated by `start`, and is stopped only through verified readiness IPC. See `.pf/artifacts/runtime-daemon-lifecycle-20260814/daemon-lifecycle-orphaned-instance-report.md`.
