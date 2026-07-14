# Project Snapshot Refactor Review

## Reviewed Object

Project Snapshot, Session Bootstrap, and Telemetry refactor.

## Reviewer

ProcessForge self-review

## Result

pass_with_conditions

## Findings

- PASS: `.pf` project flow root is supported for new projects.
- PASS: project init does not create root project `AGENTS.md` by default.
- PASS: global agent instructions are updated only inside ProcessForge markers.
- PASS: snapshot YAML and Markdown are generated and freshness can be checked.
- PASS: session start writes private metadata and NDJSON telemetry.
- PASS: assignment capsule requires structured YAML front matter or assignment YAML.
- PASS: public cleanliness and schema validation pass.
- WARN: optional capabilities `browser_verification` and
  `official_documentation_lookup` are unresolved in the current repository.
- WARN: current repository remains legacy root layout pending migration review.

## Required Follow-Up

- Review `artifacts/pf-layout-migration-proposal.md` before any root-to-`.pf`
  move.
- Add deeper tool/MCP health checks when registries carry real provider data.

## Evidence

- `artifacts/project-snapshot-refactor-report.md`
- `contexts/project-context.snapshot.yaml`
- `contexts/project-context.snapshot.md`
- `tools/processforge.py`
- `schemas/project-context-snapshot.schema.json`
- `schemas/session-telemetry-event.schema.json`

## Recommendation

Accept this as Stage 1 support with migration deferred.
