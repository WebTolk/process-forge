# R03 task index

1. Map the explicit updater concurrency contract in `core_update.py`, existing
   migration smokes, and review evidence.
2. Build two separate archive payloads and a shared disposable Workplace under
   `.pf/tmp/r03-workplace-migration-race`.
3. Plan both `copy_if_missing` operations before either applies; force both
   apply paths to their target-write boundary at the same time.
4. Verify whether one caller overwrites the other and classify the result
   against the documented support contract. Do not alter source in this run.

The primary agent owns the disposable probe and report. No concurrent writer
owns any product file.