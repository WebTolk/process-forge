# Search Index Recovery Report

Run: `operational-hardening-search-update-20260822`

## Implemented Recovery

- `index_status()` now reports `LocalSearchError.code` instead of dataclass string output.
- `maintenance_tick()` rebuilds degraded derived DB state except for true capability failure `fts5_unavailable`.
- Failed refresh/rebuild is returned as a degraded maintenance result instead of an unhandled crash.
- Schema mismatch recovery is covered by smoke.

## Smoke Evidence

`tools/smoke_search_update_operational_hardening.py` mutates `meta.schema_version` to `999`, verifies `index_schema_mismatch`, runs `maintenance_tick`, and verifies `action=rebuild` with final `status=fresh`.

## Non-Goals

No second source of truth was introduced. The index remains rebuildable derived state.
