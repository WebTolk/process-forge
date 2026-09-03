# ProcessForge 1.1.0 Current State Audit

Date: 2026-08-23

## Git

- Branch at intake: `dev`.
- Remote at intake: `origin/dev`.
- Intake HEAD: `bbcae29 chore: record resource indexing completion report`.
- Intake dirty files: generated `.pf/artifacts/projections/command-history.md`
  and `.pf/artifacts/projections/stage-obligations.json`.

## Version And Release Metadata

- Intake `VERSION`: `1.0.2`.
- Updated target `VERSION`: `1.1.0`.
- Updated CLI constants: `PROCESSFORGE_VERSION=1.1.0`,
  `RELEASE_ARCHIVE_VERSION=1.1.0`.
- Updated `.pf/process-forge.yaml` project ProcessForge version and
  `project.process-forge` knowledge-stack version to `1.1.0`.
- Updated `updates/processforge-update-index.yaml` current/latest stable to
  `1.1.0` and added a non-mandatory migration guide.

## Dist

- `dist/` contains the canonical public pair only:
  `processforge.zip` and `processforge.manifest.json`.
- No named stale prerelease/archive ZIPs remain in `dist/`.

## Baseline Gates Before Refactor

- PASS: schema validation.
- PASS: public cleanliness.
- PASS: checksum inventory.
- PASS: release-check.
- PASS: py_compile after rerun with explicit Python file list.
- PASS: critical smokes for Runtime, update manifest/apply, freshness/readiness,
  project init local MCP/search, resource indexing policy, and project init.
- EXPECTED BLOCKER: release manifest provenance smoke failed while the tree was
  dirty with this active run and regenerated project-context artifacts. It must
  be rerun from a committed clean source.

## Project Context

- Initial `project-context-refresh` wrote `ctx-20260823-171440-4b56ca`.
- Initial `project-context-check` reported `STATUS: broken` because
  `build_project_context_snapshot` treated the first `processes[]` catalog
  entry as the selected execution route.
- Root cause: `.pf/process-forge.yaml` lists enabled process definitions, but
  does not select `knowledge-package-improvement` through the scalar `process:`
  field.
- Remediation: removed the implicit first-process fallback and added
  `tools/smoke_process_catalog_not_implicit_execution_route.py`.
- Confirmed after remediation:
  `project-context-refresh` wrote `ctx-20260823-174027-b6cf66`;
  `project-context-check --json` returned `status=fresh`,
  `resource_readiness.status=fresh`, and `execution_readiness.status=ready`.
- Assignment capsule was created at
  `.pf/contexts/assignment-capsules/prerelease-1-1-0-python-refactor-main.capsule.yaml`.
