# Runtime liveness remediation

Status: done

## Input

Independent review artifact: `.pf/artifacts/runtime-final-independent-review-20260814/runtime-final-independent-review.md`.

## Remediated findings

### Concurrent startup before endpoint publication

`tools/pf_runtime/service.py` now distinguishes a live singleton that is genuinely starting from a stale ready record with an unusable endpoint. A live lock with a `starting`, `stopped`, or absent service state is preserved; a concurrent `runtime start` waits for readiness and then reports the existing instance instead of deleting the lock and spawning a second daemon. The child-side singleton acquisition applies the same rule.

The distinction deliberately preserves prior stale PID-reuse recovery: a live PID paired with a `ready` service record whose endpoint fails `/readyz` is still treated as stale rather than as a valid starting instance.

### Stop before endpoint publication

`runtime stop` now detects a live starting singleton. It waits briefly for endpoint publication; if readiness cannot appear, it terminates the process identified by that local singleton lock, waits for exit, and cleans stale state. It no longer reports `not running` while that start-owned process is alive.

## Regression coverage

`tools/smoke_long_lived_runtime.py` now creates a deterministic live, endpoint-unpublished singleton state and proves that:

1. a second `runtime start --timeout 1` fails as still starting without removing the live lock or launching a competing instance;
2. `runtime stop --timeout 1` reports stopped and terminates that process; and
3. the pre-existing dead-PID and live-PID-with-dead-endpoint stale-recovery checks still pass.

## Verification

- `python -m py_compile tools/pf_runtime/service.py tools/smoke_long_lived_runtime.py` — pass.
- `python tools/smoke_long_lived_runtime.py` — pass.
- `python tools/smoke_runtime_host_poc.py` — pass.
- `python tools/smoke_codex_exec_worker.py` — pass.
- `python tools/processforge.py release-test --root . --only smoke_runtime_host_poc --only smoke_long_lived_runtime --only smoke_codex_exec_worker --fail-fast` — pass in 64.26 s.
- `python tools/validate-process-forge-schemas.py --root .` — pass.
- `git diff --check` — pass; only pre-existing line-ending notices.

## Residual risk

The lock is local operational authority, not a cryptographic process identity. As noted in the prior runtime report, an adversarially modified local runtime directory or extremely rapid PID reuse cannot be distinguished perfectly without a stronger process identity in a future slice. PF Core remains untouched.
