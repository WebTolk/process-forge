# Public Core Inventory

Audit date: 2026-07-25.

Public release surface is limited to product files under `bin/`, `checksums/`, `docs/`, `examples/`, `packages/`, `policies/`, `processes/`, `prompts/`, `schemas/`, `seeds/`, `templates/`, `tools/`, and `updates/`, plus root metadata files.

Public smoke tests retained in `tools/`:

- `smoke_first_run.py`
- `smoke_runtime_driver_registry.py`
- `smoke_worker_run_shell.py`
- `smoke_process_supervisor_tick.py`
- `smoke_process_run_task_batch.py`

Dogfooding smoke tests moved to `.pf/dogfooding/tests/scripts/` and grouped in `.pf/dogfooding/tests/manifest.yaml`.

The checksum inventory moved from `.pf/artifacts/checksum-inventory.sha256` to `checksums/processforge.sha256` so the public archive can exclude `.pf/artifacts/` completely.
