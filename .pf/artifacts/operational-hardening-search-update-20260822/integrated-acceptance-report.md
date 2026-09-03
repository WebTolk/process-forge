# Integrated Acceptance Report

Run: `operational-hardening-search-update-20260822`

## Passed

- `tools/smoke_search_update_operational_hardening.py`
- `tools/smoke_project_init_local_search_mcp.py`
- `tools/smoke_core_update_manifest.py`

## Covered

- Search add/change/delete.
- Template resource search.
- Dirty mark from PF resource event.
- Schema-degraded derived DB recovery.
- Search and maintenance concurrency smoke.
- Core update file failure journal.
- Core repair classification `safe_to_rollback`.

## Not Executed

- Live Codex host `/hooks` and `/mcp`.
- Real OS locked-file handle smoke.
- Runtime daemon stop/start integration.
