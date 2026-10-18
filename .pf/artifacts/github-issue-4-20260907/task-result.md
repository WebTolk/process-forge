# Task Result: GitHub Issue #4

Result: ready_for_review

Implemented a compatible, archive-declared Workplace migration for the
1.0.2-to-1.1.0 transition. `core-update plan` and `apply` accept
`--workplace-root`; the migration adds missing `codex-exec` files and registry
entries only, preserves existing configuration, journals backups, and runs a
post-update Workplace doctor after confirmed apply.

Validation passed:

- `python tools/smoke_core_update_manifest.py`
- `python -m py_compile src/processforge_core/core_update.py tools/processforge.py tools/smoke_core_update_manifest.py`
- schema validation, public cleanliness, checksum check, and `git diff --check`

Residual boundary: public `release-test` is blocked by pre-existing stale
archives in `dist/`; no release artifact was removed or replaced.
