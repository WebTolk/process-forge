# F01 Search Worker Report

## Changes

- `garage.py`: retained Workplace-scoped maintenance/readiness; queries now use the project runtime snapshot and project root, enforcing authorization in totals, pagination, and results.
- Restored `TemporaryDirectory` context managers in both public Garage smokes.
- Retained real Workplace registration and strengthened cross-project, pagination, empty-authorization, resolve-denial, and session-mismatch checks.

## Baseline

Audit evidence records the original failure at baseline commit `1aecc18b6824204ca45ab30241b92d26e6d583a5`: a forbidden resource was searchable with `total=1` despite `pf.resolve` denying it. The baseline reproduction was not rerun by this worker; the brief directs primary to perform isolated regression evidence.

## Checks

- `python -m py_compile ...` — PASS, exit 0.
- Scoped `git diff --check` — PASS, exit 0.
- Full stdio smokes and `smoke_project_resource_narrowing_search.py` — NOT RUN due the worker sandbox’s documented temporary-directory permission limitation.

Primary should run the modified smokes and isolated baseline-vs-fixed regression outside this sandbox.