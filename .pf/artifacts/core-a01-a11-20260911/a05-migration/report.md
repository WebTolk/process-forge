# A05 Migration Report

Status: implemented; ready for review.

## Changed files

- `src/processforge_core/core_update.py`
  - Validates migration sources during planning.
  - Blocks missing, directory, and invalid sources.
  - Preserves valid existing targets.
  - Records structured failed journals for apply-time archive errors.
- `tools/smoke_core_update_migration_sources.py`
  - Adds ZIP regressions for source validation, preservation, and recovery.
  - Supports `--root` for disposable fixtures.

## Verification

- PASS: AST parsing.
- PASS: `git diff --check`.
- BLOCKED: Runtime smoke hit the first sandbox `PermissionError` creating a system-temp directory. No workaround was attempted.
- Unexecuted: `python tools/smoke_core_update_migration_sources.py --root .pf/tmp/a05-migration`

No installed distribution, versions, checksums, or release metadata were changed.