# Controlled Finish Report

- Date: 2026-07-30
- Assignment: `.pf/assignments/remediation-controlled-finish-20260730.yaml`
- Owner: `root-orchestrator`
- Product writer: root only
- Agent policy: report-only agents, no product writes
- Status: ready for independent review

## Scope

This slice deliberately stayed narrow after the user confirmed release
`1.0.0` and rejected broad rewrites. It closes the failed transaction review
items that were already reproduced and corrects the accidental public
`schema_version: 2` contract for reusable templates.

Out of scope:

- full release-manifest implementation;
- lifecycle/provider/runtime implementation;
- broad removal of every historical compatibility alias outside the affected
  transaction commands;
- internal dogfooding workplace migration.

## Product Changes

### Transaction Layer

- `AuthoringEffect` now stores serializable `kind`, `payload` and executable
  metadata.
- Journals now persist ordered `post_commit_effects` with `pending`,
  `running`, `succeeded`, `failed` and `not_executable` states.
- Terminal authoring states are `rolled_back` and
  `committed_audit_complete`; `committed`, `committed_audit_pending` and
  `recovery_required` block later mutations.
- Rollback and recovery now verify exact pre-existing SHA-256 hashes and
  absence of pre-missing destinations before writing `rolled_back`.
- Backup hash mismatch leaves `recovery_required` instead of pretending
  rollback succeeded.
- Added `authoring-transaction-recover --runtime-root ... --transaction ...
  (--dry-run|--apply)` to replay pending post-commit effects or finish
  verified rollback.

### Platform Authoring

- `build_platform_authoring_plan` now runs staged semantic validation before
  entity or registry publication.
- Platform resolution accepts staged contract overrides for validation only,
  so missing parent platforms fail before the contract is committed.
- `platform.contract.doctor.passed` and
  `platform.authoring.completed` are emitted only after staged checks pass.

### Post-Commit Effects

- Process events, knowledge audit artifacts/events and platform audit
  artifacts/events now use durable effect descriptors.
- Event/proposal sinks use stable ids derived from the effect id so replay does
  not duplicate already completed effects.
- Conditional hook rows remain visible in dry-run plans but are marked
  non-executable in the journal.

### Contract Versioning

- Reusable template manifests are now first-public-contract
  `schema_version: 1`.
- `template-create`, `schemas/reusable-template.schema.json`,
  `templates/reusable-template-template.yaml`,
  `tools/smoke_remediation_schema_inventory.py` and
  `tools/smoke_remediation_generator_schema_alignment.py` were synchronized.
- Governing ADR language was corrected from accidental v2/v1.1.0 wording to
  `schema_version: 1` and release `1.0.0`.

### Public Cleanliness

Remediation smoke fixtures were renamed from domain-looking identifiers to
neutral `platform.example-*` / `docs.example-*` ids. Diagnostic string
literals that looked like Windows paths to the public-cleanliness regex were
rewritten without changing test behavior.

## Validation

Passed:

- `python -m py_compile tools/processforge.py
  tools/smoke_remediation_transactional_authoring.py
  tools/smoke_remediation_schema_inventory.py
  tools/smoke_remediation_generator_schema_alignment.py`
- parser import/build check
- `python bin/pf.py --help`
- `python tools/smoke_remediation_transactional_authoring.py`
- `python tools/smoke_remediation_platform_layout_strict.py`
- `python tools/smoke_remediation_process_create_transaction.py`
- `python tools/smoke_remediation_schema_inventory.py`
- `python tools/smoke_remediation_generator_schema_alignment.py`
- `python tools/smoke_remediation_aggregate_gates.py`
- `python tools/smoke_remediation_security_boundaries.py`
- `python tools/smoke_remediation_doctor_contracts.py`
- `python tools/validate-process-forge-schemas.py`
- `python tools/validate-public-cleanliness.py`
- `git diff --check`

`git diff --check` returned exit code 0. It still prints expected Windows
LF-to-CRLF normalization warnings for many dirty working-copy files.

## Residual Risk

The broader pre-release run is not complete. Remaining work includes release
archive integrity, lifecycle/provider-runtime implementation, and the filtered
strict-contract backlog. Those must be handled as separate narrow slices.
