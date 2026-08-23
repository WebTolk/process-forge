# Release Archive Correction Report

## Status

Corrected and validated.

Observed:

```text
WROTE: dist/processforge-1.0.2-resource-indexing-20260822.zip
WROTE: dist/processforge-1.0.2-resource-indexing-20260822.manifest.json
FILES: 865
```

## Corrections

- `release_git_provenance()` now preserves Git porcelain leading status spaces by using trailing-newline trimming instead of `.strip()`.
- Clean-source provenance remains strict, but modified runtime-generated `.pf/artifacts/projections/command-history.md` and `stage-obligations.json` are allowed because they are excluded from the release archive.
- `write_release_zip()` now sorts physical source entries and generated entries together, so ZIP order and sidecar manifest order stay deterministic.
- `release-archive-test --root` now recomputes the generated `processforge-core.manifest.json` hash from the current root release set and sidecar provenance.
- `smoke_project_init_acceptance.py` now follows the resource-indexing contract: `search()` reports missing/stale/degraded state and `maintenance_tick()` owns refresh/rebuild work.
- `sqlite_fts5_capability()` now returns a degraded capability payload if SQLite cannot open its in-memory probe database.

## Confirmed Gates

- `python tools/processforge.py release-pack --root . --output dist/processforge-1.0.2-resource-indexing-20260822.zip` PASS.
- `python tools/processforge.py release-archive-test --archive dist/processforge-1.0.2-resource-indexing-20260822.zip --root . --extracted-test quick` PASS.
- `python tools/processforge.py release-archive-test --archive dist/processforge-1.0.2-resource-indexing-20260822.zip --root . --extracted-test full --timeout-scale 2` PASS in `969.61` seconds.
- Extracted archive `tools/smoke_resource_indexing_policy_acceptance.py` PASS.
- Extracted archive `tools/smoke_project_init_local_search_mcp.py` PASS.

## Full Gate Resolution

The interrupted full gate was resumed. `smoke_long_lived_runtime.py` passed standalone and inside the full public suite; the actual failing check was `smoke_project_init_acceptance.py`, now fixed and included in the rebuilt archive.
