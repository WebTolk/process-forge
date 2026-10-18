# Implementation

## Changed Files

- `tools/processforge.py`
- `tools/smoke_release_archive_timeout_scale.py`
- `docs/known-limitations.md`
- `docs/ru/known-limitations.md`
- `.pf/logs/evolve-20261002-28.md`
- `.pf/artifacts/evolve/evolve-20261002-28/*`

## Change Summary

Implemented a shared `positive_timeout_scale(args)` helper that treats only missing/`None` as the default `1.0`, rejects zero, negative, `nan`, and `inf`, and prints a clear failure.

Updated `release-test`, `dev-test` / `dogfood-test`, and `release-archive-test` to use the shared validator. `release-archive-test` now appends `--timeout-scale <scale>` to the nested extracted `release-test` command and continues to scale the outer extracted-test process timeout separately.

Added `tools/smoke_release_archive_timeout_scale.py` to capture nested argv and outer timeout without running a full release archive qualification. Updated CLI help and EN/RU known limitations documentation.

## Scope Check

All product edits stayed inside the Work write scope. No Runtime/MCP/installed Core/release publication actions were performed.
