# Core Updater Implementation Report

Run: `core-updater-manifest-implementation-20260822`
Task: `core-updater-manifest-first-slice-20260822`

## Implemented

- Added `src/processforge_core/core_update.py` as a core updater service.
- Added manifest contract `processforge-core.manifest.json`.
- Integrated generated core manifest into `release-pack` archives.
- Preserved release determinism by using release provenance `generated_at`.
- Added CLI:
  - `core-update status`
  - `core-update plan`
  - `core-update apply`
  - `core-update repair`
- `plan` is read-only and validates archive manifest paths/checksums.
- `apply` requires `--confirm`.
- `apply` deletes only obsolete PF-owned files from the old manifest.
- Unknown files are preserved.
- Locally modified PF-owned files block apply by default.
- New installed manifest is written last.
- Runtime update state and backups are stored under `<core>/runtime/core-update/`.
- Added EN/RU docs:
  - `docs/concepts/core-update-manifest.md`
  - `docs/ru/concepts/core-update-manifest.md`
- Added smoke:
  - `tools/smoke_core_update_manifest.py`

## Validation

- `python -m py_compile src/processforge_core/core_update.py tools/processforge.py tools/smoke_core_update_manifest.py`
- `python tools/processforge.py core-update --help`
- `python tools/smoke_core_update_manifest.py`

## Release-Pack Validation Note

`python tools/processforge.py release-pack --root . --output .pf/tmp/core-update-release-dry-run/processforge.zip --dry-run` was attempted, but current public-cleanliness preflight fails on pre-existing non-neutral documentation package IDs in `.pf/process-forge.yaml`. This is outside this slice and was not modified.

## Remaining From Master Prompt

- Automated `repair` continue/rollback, beyond incomplete-state reporting.
- Runtime/MCP owned process stop/start/health integration.
- Dedicated Windows locked-file smoke using a live locked handle.
- Full release/archive validation after public-cleanliness blockers are removed.
- Independent review.
- Final full validation artifact.
