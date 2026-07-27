# Built-in Process Catalog Audit Report

Timestamp: 2026-07-27T12:04:00+04:00
Agent/role: main implementation agent
Status: pass

## Summary

- Processes audited: `32`
- Public stable: `30`
- Public experimental: `1`
- Internal maintenance: `1`
- Failures: `0`
- Warnings: `0`

## Classification

- `INTERNAL_MAINTENANCE`: `1`
- `PUBLIC_EXPERIMENTAL`: `1`
- `PUBLIC_STABLE`: `30`

## Contract Coverage

- All public stable processes declare `execution_mode`, `coordination_requirements`, `error_handling`, `responsibility_boundaries`, `stage_completion`, and `run_completion`.
- Stage produced artifacts are declared in `artifact_definitions` or explicit artifact sections.
- Deprecated `stages[].handoff_required` was migrated out of public stable process definitions.
- `context-resolution` now has `templates/context-cache.yaml` for the previously missing template reference.
- Package manifests now expose `processes`, `stable_processes`, `experimental_processes`, and `internal_processes`.

## Validation

- `builtin-process-catalog-doctor --public`: PASS.
- New direct smokes: PASS.
- New release-test `--only` smokes: PASS.
- Full public release-test fail-fast: PASS.
- Full public release-test: PASS.
- Release archive test with full extracted test: PASS.
- Clean extracted archive new smokes, catalog doctor, and public fail-fast: PASS with expected non-git warning.
