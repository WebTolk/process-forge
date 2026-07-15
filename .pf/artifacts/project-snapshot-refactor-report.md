# Project Snapshot Refactor Report

## Status

implemented

## Scope

Implemented the file-first Project Context Snapshot, `.pf` project flow root,
session telemetry, bounded global agent section, and assignment front matter
support for ProcessForge.

This repository itself remains on the legacy root layout for now. The new tools
support both layouts. No existing root-level flow folders were moved.

## Implemented

- `init-project` now creates `.pf/AGENTS.md`, `.pf/process-forge.yaml`,
  `.pf/process-forge.local.yaml`, and `.pf/*` flow directories by default.
- Root project `AGENTS.md` is no longer created by project init.
- `global-agents-section` inserts or updates only the marker-bounded
  ProcessForge section.
- `project-context-refresh` writes project context snapshot YAML and Markdown.
- `project-context-check` checks `valid_until`, source fingerprints, source
  additions/removals, and required capability availability.
- `session-start` prefers the project context snapshot and writes private
  session metadata plus NDJSON telemetry.
- `assignment-capsule` creates a snapshot-based capsule only from YAML front
  matter or assignment YAML.
- Required missing capabilities block assignment capsules; optional missing
  capabilities warn.
- Runtime/session/telemetry paths are ignored for `.pf` and legacy root runtime.
- Schema and public-cleanliness validators know the new snapshot, telemetry,
  session metadata, assignment front matter, and `.pf` public/private split.

## Files Added

- `docs/concepts/project-context-snapshot.md`
- `docs/concepts/session-telemetry.md`
- `docs/concepts/global-agent-section.md`
- `docs/concepts/project-flow-root.md`
- `docs/concepts/assignment-front-matter.md`
- `docs/concepts/context-freshness.md`
- `schemas/project-context-snapshot.schema.json`
- `schemas/session-metadata.schema.json`
- `schemas/session-telemetry-event.schema.json`
- `schemas/assignment-front-matter.schema.json`
- `templates/project-context.snapshot.yaml`
- `templates/project-context.snapshot.md`
- `templates/global-agents-processforge-section.md`
- `templates/session-metadata-template.yaml`
- `templates/assignment-front-matter-template.md`
- `contexts/project-context.snapshot.yaml`
- `contexts/project-context.snapshot.md`
- `contexts/processforge-project-snapshot-session-telemetry-master-prompt.*`

## Files Updated

- `tools/processforge.py`
- `tools/validate-process-forge-schemas.py`
- `tools/validate-public-cleanliness.py`
- `.gitignore`
- `.processforge-releaseignore`
- selected docs and templates that previously described root layout as default
- `contexts/context-index.yaml`
- `contexts/resolved-rules.yaml`
- `contexts/context-conflict-report.md`

## Current Repository Layout

The current ProcessForge repository still uses legacy root layout:

```text
process-forge.yaml
contexts/
assignments/
artifacts/
logs/
reviews/
handoffs/
```

For that reason, this run generated the repository snapshot under:

```text
contexts/project-context.snapshot.yaml
contexts/project-context.snapshot.md
```

Newly initialized projects use `.pf/`.

## Verification

Passed:

- `python -m py_compile tools\processforge.py tools\validate-process-forge-schemas.py tools\validate-public-cleanliness.py`
- `python tools\processforge.py project-context-refresh --project-root .`
- `python tools\processforge.py project-context-check --project-root .`
- `python tools\processforge.py context-resolve --project-root .`
- `python tools\processforge.py doctor-context --project-root . --assignment задания\processforge_project_snapshot_session_telemetry_master_prompt.md`
- `python tools\validate-process-forge-schemas.py --root .`
- `python tools\validate-public-cleanliness.py --root .`
- `python tools\validate-process-forge-checksums.py --root .`
- `git diff --check` returned no whitespace errors; Git printed line-ending
  normalization warnings for modified text files.

Temporary `.pf` project smoke checks passed:

- `init-project` created `.pf/AGENTS.md` and did not create root `AGENTS.md`.
- `project-context-refresh` wrote `.pf/contexts/project-context.snapshot.yaml`
  and `.pf/contexts/project-context.snapshot.md`.
- `project-context-check` reported `STATUS: fresh`.
- `assignment-capsule` wrote `.pf/contexts/assignment-capsules/pf-test-assignment.capsule.yaml`.
- Optional missing `repository.symbol_analysis` produced a warning.
- Required missing capability blocked capsule creation.
- Source fingerprint changes and expired `valid_until` reported `STATUS: stale`.
- `global-agents-section` preserved existing user content and was idempotent.

## Known Warnings

- Snapshot health is `warn` in this repository because optional capabilities
  `browser_verification` and `official_documentation_lookup` do not have
  resolved providers in the current manifest/registry set.
- The current assignment master prompt has no YAML front matter, so it is
  human-readable only for the new assignment capsule model. A legacy ECP was
  created to satisfy the current repository boot sequence.
- Existing deleted files `processforge_init_master_prompt.md` and
  `processforge_master_prompt.md` predated this run and were not restored.

## Residual Risks

- Snapshot generation is intentionally MVP-level and does not perform deep
  registry health checks for tools/MCP beyond declared capability resolution.
- Global agent adapter snippets beyond marker-bounded generic files are
  documented as future extension points, not implemented as separate adapters.
- Full migration from root layout to `.pf/` is intentionally deferred pending
  review.
