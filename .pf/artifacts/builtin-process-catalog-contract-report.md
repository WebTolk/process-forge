# Built-in Process Catalog Contract Report

Timestamp: 2026-07-27T12:04:00+04:00
Agent/role: main implementation agent
Status: delivered and validated

## Delivered

- Added `builtin-process-catalog-doctor` with text, JSON, public mode, and report output.
- Added strict public stable process contract checks for behavioral fields, companions, produced artifacts, gates, deprecated handoff fields, and template references.
- Updated `process-definition.schema.json` and `process-authoring-answers.schema.json` for the current PF process model.
- Updated process authoring materialization so behavioral fields are preserved instead of silently dropped.
- Classified all 32 built-in processes: 30 public stable, 1 public experimental, 1 internal maintenance.
- Repaired public stable process metadata, roles, stages, artifacts, gates, completion semantics, package ownership, docs, prompts, and examples.
- Added `templates/context-cache.yaml`.
- Moved quality-audit dogfooding-looking example outputs under `examples/process-authoring/quality-audit/expected/` with generic expected names.
- Added four deterministic public smokes and wired them into `release-test --public`.

## Files Added Or Updated

- `tools/processforge.py`
- `tools/smoke_builtin_process_catalog.py`
- `tools/smoke_process_authoring_materialization_parity.py`
- `tools/smoke_process_definition_schema_contract.py`
- `tools/smoke_builtin_process_pack_completeness.py`
- `schemas/process-definition.schema.json`
- `schemas/process-authoring-answers.schema.json`
- `templates/process-definition-template.yaml`
- `templates/process-authoring-answers.yaml`
- `templates/context-cache.yaml`
- `processes/*.yaml`
- `packages/*.yaml`
- `docs/processes/*.md`
- `prompts/*-agent.md` for missing stable companions
- `examples/process-authoring/**`

## Validation

- `python -m py_compile ...`: PASS.
- `python tools/validate-process-forge-schemas.py --root .`: PASS.
- `python tools/validate-public-cleanliness.py --root .`: PASS.
- `python tools/validate-process-forge-checksums.py --root . --check`: PASS.
- Direct new smokes: PASS.
- `python bin/pf.py builtin-process-catalog-doctor --root . --public`: PASS.
- Four new `release-test --only ... --public --fail-fast` checks: PASS.
- `python bin/pf.py release-test --root . --public --fail-fast --timeout-scale 1`: PASS.
- `python bin/pf.py release-test --root . --public --timeout-scale 1`: PASS.
- `python bin/pf.py release-pack --root . --output dist/processforge.zip`: PASS, 595 files.
- `python bin/pf.py release-archive-test --archive dist/processforge.zip --root . --extracted-test full --timeout-scale 1`: PASS.
- Clean extracted archive proof root: `C:/Users/musst/AppData/Local/Temp/pf-process-catalog-final-fef15931bca84dc9ae48b9edac9d5c20`; new smokes and catalog doctor PASS; public fail-fast PASS with expected non-git warning.
- `git diff --check`: PASS, with Git CRLF working-copy warnings only.

## Remaining Limitations

- `orchestrator-shell-agents-supervision` is explicitly public experimental, not a public stable reference process.
- `authoring-parity-audit` is explicitly internal maintenance.
- No UI, database, network hooks, real external agent drivers, or `.ps1` files were added.
