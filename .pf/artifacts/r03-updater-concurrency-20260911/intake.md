# R03 intake: Workplace migration concurrency

Objective: determine whether independent concurrent updater applications to one
Workplace are a supported contract, and reproduce a race only in disposable
fixtures if that path is possible. No installed Core, release, publication or
production source change is in scope.

Starting evidence: static review observed that migration planning tests
`copy_if_missing` and registry uniqueness before apply, whereas
`apply_workplace_migration()` writes planned operations without rechecking the
target. `apply_update()` does not acquire an interprocess lock before calling
that routine.

Acceptance:

1. Establish the documented/supported concurrency contract from source and
   existing tests.
2. Use only `.pf/tmp/r03-*` fixtures for any concurrent execution.
3. Report a confirmed race only if it is reproducible; otherwise retain it as
   an unverified design limitation.
4. Do not apply updates to installed Core or alter source without confirmation.