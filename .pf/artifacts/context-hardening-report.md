# Context Hardening Report

## Scope

Assignment: `processforge_context_hardening_assignment.md`.

Implemented hardening for assignment-specific context compilation, context doctoring, generated context schemas, checksum verification, ECP immutability, missing-workplace init safety, release cleanliness, and context source classification.

## Changes

- `context-compile` now recomputes context for the requested assignment, writes an assignment-specific conflict report, blocks `blocked` and unapproved `requires_approval` contexts, and refuses to overwrite an existing default ECP/capsule unless `--supersede` is used.
- `doctor-context --assignment` now recomputes assignment context status, checks assignment-specific conflict status, checks ECP `context_status`, validates the conflict report reference, and verifies the ECP `context_index` checksum.
- Generated ECP files now carry immutable snapshot fields: assignment identity, context status, conflict metrics, source fingerprints, selected tools/templates, selected actions, checksums, and a package checksum.
- Schema validation now performs real local JSON Schema validation for manifests, process definitions, package manifests, context index, resolved rules, ECP files, capsule files, and workplace manifests.
- Checksum validation now supports `--write`, `--check`, and default check mode when an inventory exists.
- `init-project --apply` now fails by default when `--workplace` points to a missing file; `--allow-missing-workplace` is the explicit escape hatch.
- `.processforge-releaseignore` now keeps public skeleton README files while excluding dogfooding outputs, local/private files, runtime/cache state, IDE state, and Python cache files.
- `contexts/context-index.yaml` now records `selection_reason` and `load_policy` so broad project sources are distinguishable from required assignment inputs.

## Results

- `python tools/processforge.py context-resolve --project-root .` passed with status `warn` for optional capability warnings.
- `python tools/processforge.py context-compile --project-root . --assignment assignments/processforge-session-bootstrap-implementation.md --capsule` created the assignment conflict report, ECP, and capsule.
- `python tools/processforge.py doctor-context --project-root . --assignment assignments/processforge-session-bootstrap-implementation.md` passed with an assignment warning, not a blocking failure.
- `python tools/validate-process-forge-schemas.py --root .` passed.
- `python tools/validate-public-cleanliness.py --root .` passed.
- Negative schema smoke passed: an invalid generated ECP caused schema validation to fail.
- Negative checksum smoke passed: `--check` passed on a fresh temp inventory and failed after modifying the temp public file without `--write`.
- Negative context smoke passed: an assignment with `unknown.required.capability` failed `context-compile`, produced only a conflict report, and did not create ECP/capsule.
- ECP immutability smoke passed: repeated `context-compile` for the same assignment failed with `ECP already exists`.
- Missing-workplace smoke passed: `init-project --apply --workplace <missing>` failed and did not write `process-forge.local.yaml`.
- Explicit missing-workplace escape hatch passed: `init-project --apply --allow-missing-workplace` proceeded and wrote the local manifest in a temp project.

## Negative Tests

- Unknown required capability blocks ECP/capsule creation.
- `doctor-context --assignment` fails for the blocked assignment.
- Invalid generated ECP fails schema validation.
- Stale checksum inventory fails `--check`.
- Repeated compile does not overwrite the existing ECP silently.
- Missing workplace blocks apply-mode project initialization.
- `--allow-missing-workplace` works only as an explicit escape hatch.

## Remaining Warnings

- The main assignment context remains `warn` because optional capabilities are unresolved. This is expected and non-blocking.

## Known Limitations

- The built-in schema validator intentionally supports the JSON Schema subset used by this repository.
- Capability provider merging is registry-ready but still heuristic until richer workplace/project registries are introduced.

## Timestamp

2026-07-13T16:45:25+04:00
