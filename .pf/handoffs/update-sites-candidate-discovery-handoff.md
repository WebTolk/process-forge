# Handoff: primary-agent -> operator

Objective:
Implement the unified ProcessForge update-site updater MVP.

Current status:
Implementation complete through schemas, CLI lifecycle, docs, deterministic smokes, checksum refresh, full public release-test, release packaging, archive test, and clean extracted archive proof.

Input artifacts:
- `задания/processforge_update_sites_unified_updater_mvp_master_prompt.md`
- `.pf/artifacts/update-sites-candidate-discovery-report.md`
- `.pf/reviews/update-sites-candidate-discovery-review.md`

Files changed:
- `tools/processforge.py`
- `tools/validate-process-forge-schemas.py`
- `tools/update_smoke_helpers.py`
- `tools/smoke_update_*.py`
- `schemas/update-*.schema.json`
- package/tool/platform/MCP/template update schema surfaces
- update docs and README/QUICKSTART pages
- `updates/processforge-update-index.yaml`
- `checksums/processforge.sha256`

Files not to touch:
- Generated workplace/runtime update caches from smoke tests are temp-only and not part of the repository.
- Project `.pf` remains assessment/migration only, not downloadable package overlay.

Known issues:
- Provider-specific release APIs are planned, not implemented.
- Self-update apply over source checkout is conservative/manual.

Required checks:
All assignment-required checks have passed in this run. Run `git diff --check` once more immediately before commit.

Next recommended action:
Review the implementation diff and prepare commit if requested.
