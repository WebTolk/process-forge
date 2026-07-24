# Runtime Driver Registry And Process Supervisor MVP Report

Status: implemented.

Implemented scope:

- Added neutral runtime driver schemas and templates for `manual`, `generic-shell`, and `test-echo-worker`.
- Added `runtime-driver list/validate/describe` and flat aliases.
- Added `worker-run prepare/start/status/stop/collect` and flat aliases.
- Added `supervisor tick/run/status/stop` and flat aliases.
- Added `.pf/runtime/agent-runs/<run-id>/<task-id>/` state files: `status.json`, `command.json`, `process.json`, `exit.json`, `stdout.log`, `stderr.log`, `heartbeat.json`, and collection report.
- Added `.pf/runtime/supervisor/` state and last tick report.
- Extended orchestrator plans with `runtime.default_driver`, `runtime.supervisor_profile`, `runtime.start_policy`, worker `runtime_driver`, and `depends_on`.
- Added dependency-aware write-scope overlap handling for sequential worker tasks.
- Added process definitions `runtime-driver-registry` and `process-supervisor`.
- Added EN/RU docs, minimal example, and smoke tests.

Validation evidence:

- `python -m py_compile tools\processforge.py tools\validate-process-forge-schemas.py tools\validate-public-cleanliness.py tools\smoke_runtime_driver_registry.py tools\smoke_worker_run_lifecycle.py tools\smoke_process_supervisor.py tools\test_workers\echo_worker.py`
- `python tools\smoke_runtime_driver_registry.py`
- `python tools\smoke_worker_run_lifecycle.py`
- `python tools\smoke_process_supervisor.py`
- `python tools\validate-process-forge-schemas.py --root .`
- `python tools\validate-public-cleanliness.py --root .`
- `git diff --check`
- `python bin\pf.py release-test --root .`
- `python bin\pf.py release-pack --root . --output dist\processforge.zip`
- `python bin\pf.py release-archive-test --archive dist\processforge.zip`

Notes:

- Built-in runtime drivers remain neutral and opt-in.
- `manual` remains the safe default and never starts a process.
- Supervisor MVP is bounded and file-first; it is not a daemon, web UI, database scheduler, or network API.
