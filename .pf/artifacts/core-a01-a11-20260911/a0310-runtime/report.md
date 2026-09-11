# a0310-runtime report

## Scope

Implemented A03, A04, and A10 in `tools/pf_runtime/service.py`, with two focused regressions:

- `tools/smoke_runtime_scheduler_failure_isolation.py`
- `tools/smoke_runtime_singleton_orphan.py`

## Changes

- Scheduler failures are isolated per project; malformed cache and missing assignments degrade health without stopping healthy ticks.
- Status reports `project_errors`, `last_scheduler_error`, and degraded health, recovering when repaired.
- Live, mismatched, missing, or unreadable singleton owners are preserved.
- Singleton lifecycle operations use a per-workplace critical section.
- Dead valid stale locks remain recoverable.
- `KeyboardInterrupt` and `GeneratorExit` behavior is preserved.

## Verification

- AST parsing passed for all changed Python files.
- `git diff --check` passed.
- Scheduler smoke was attempted but stopped on the first sandbox `PermissionError` creating its temporary fixture. No workaround was attempted.
- Singleton smoke and existing Runtime smokes remain pending primary-agent execution.

## Residual risks

End-to-end and Windows lock behavior require execution in an environment permitting disposable temporary directories.