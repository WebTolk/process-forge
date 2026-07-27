# Project Coordination Modes Handoff

Timestamp: 2026-07-27T10:06:00+04:00
Agent/role: main implementation agent
Status: ready for owner review

## Delivered

- Added workplace-level Director capability and default project mode configuration.
- Added project-level `coordination.mode` with `inherit`, `simple`, and `organized`.
- Added resolver-backed CLI for workplace/project mode status, switching, and doctor checks.
- Kept Director Office as one workplace-level office.
- Made Director inbox and Director case refresh respect effective project mode.
- Updated project snapshots and assignment capsules to expose simple vs organized obligations correctly.
- Extended process authoring and process doctor for coordination requirements and error workflow mode.
- Added deterministic public smokes for coordination hierarchy, mixed project coexistence, worker awareness, and error workflow.
- Updated docs, prompts, templates, schemas, process definitions, release checklist, and checksum manifest.

## Key Files

- `tools/processforge.py`
- `schemas/workplace.schema.json`
- `schemas/process-forge-manifest.schema.json`
- `schemas/project-context-snapshot.schema.json`
- `schemas/process-authoring-answers.schema.json`
- `templates/workplace.yaml`
- `templates/process-forge.yaml`
- `templates/project-context.snapshot.yaml`
- `templates/process-authoring-answers.yaml`
- `docs/concepts/project-coordination-modes.md`
- `docs/ru/concepts/project-coordination-modes.md`
- `tools/smoke_project_coordination_modes.py`
- `tools/smoke_mixed_workplace_projects.py`
- `tools/smoke_worker_awareness_of_director.py`
- `tools/smoke_error_workflow.py`

## Validation

- Targeted new smokes: `PASS`.
- Required existing public smokes: `PASS`.
- `validate-process-forge-schemas.py --root .`: `PASS`.
- `validate-public-cleanliness.py --root .`: `PASS`.
- `validate-process-forge-checksums.py --root . --check`: `PASS`.
- Full public `release-test`: `PASS`.
- `release-pack`: wrote `dist/processforge.zip` and manifest with 495 files.
- `release-archive-test --extracted-test full`: `PASS`.
- Clean extracted archive proof: coordination smokes `PASS`, public fail-fast `PASS with warnings` due non-git extraction.
- `git diff --check`: `PASS`.

## Follow-up Items

- None required for this task.
- Optional future work: add richer Director case lifecycle commands after the MVP proves stable in dogfooding.
