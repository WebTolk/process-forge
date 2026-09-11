# F06-F08 Independent Review

Verdict: **Bounded PASS**, with residual test/evidence limitations.

## Scope reviewed

- Diff from `5c95391`
- `tools/processforge.py`
- `tools/smoke_cli_audit_f0608.py`
- Supplied F06-F08 artifacts and baseline reproduction

## Findings

- F06 lock ownership and recovery implementation is sound for cooperating ProcessForge writers:
  - Persistent `.lock.guard` serializes acquisition, stale recovery, and release.
  - Live owners are not reclaimed solely by mtime.
  - Dead aged owners are recoverable.
  - Release verifies the complete owner record, including token.
  - Malformed, foreign, unknown-host, and live-owner records are preserved conservatively.

- F07 correctly replaces the undefined `load_json`, supports flat and nested presence records, ignores corrupt/non-object/offline records, and preserves the public Director-disable guard.

- F08 introduces one shared default-report helper. The default remains `.pf/artifacts/<safe-worker-id>-report.md`, preserving prior behavior. Normalized plans and materialized worker tasks now agree.

- The new smoke is registered in `release_test_commands`.

## Evidence

Supplied evidence shows:

- `baseline-reproduction.json`: all three original failures reproduced.
- `f0608-primary-final.txt` and `f0608-primary-final-2.txt`: focused smoke PASS.
- `f0608-public.txt`: public-copy smoke PASS.
- `f0608-schema.txt`: schema validation PASS.
- Related registry, authoring, coordination, and runtime smokes PASS.

Independent checks:

- `python -m py_compile tools/processforge.py tools/smoke_cli_audit_f0608.py`: PASS.
- Schema validation: PASS.
- In-memory F07/F08 probes: PASS.
- Full focused smoke could not complete because the Windows sandbox denied a child process’s temporary lock-file write; this is an environment limitation, not an asserted product failure.

## Residual risks

- Non-cooperating legacy processes that do not lock `.lock.guard` remain outside the new cooperative locking protocol and can theoretically race stale-file reaping.
- The smoke’s `except PermissionError: return` path skips foreign-ownership and malformed-lock assertions, so those checks are conditional on that branch not occurring.
- The supplied selective source-release test did not execute the newly registered F06-F08 smoke. POSIX locking behavior remains unverified on this Windows host.