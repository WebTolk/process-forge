# Worker lifecycle reconciliation — 2026-08-20

## Result

PASS. A detached worker that writes its durable `exit.json` is now reconciled by both `worker-run status` and `worker-run collect` before those commands inspect terminal state.

## Changed

- `worker-run status` acquires the lifecycle lock and calls the existing `observe_worker_run()` reconciliation path.
- `worker-run collect` does the same, so a finished worker is collectible without a separate supervisor tick.
- `smoke_worker_run_shell.py` adds a detached durable-exit regression and keeps all temporary smoke roots under `.pf/tmp/`.

## Validation

- `python -m py_compile tools/processforge.py tools/smoke_worker_run_shell.py`
- `python tools/smoke_worker_run_shell.py` — PASS.
- The real expanded-smoke worker state changed from stale `running` to `completed` with exit code `0` through `worker-run status`.

## Residual scope

The correction reconciles a durable exit contract; it does not attempt crash-recovery of a missing contract.
