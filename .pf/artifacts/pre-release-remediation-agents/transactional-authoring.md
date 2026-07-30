# Transactional Authoring Remediation

- Date: 2026-07-30
- Agent: `codex-remediation-transaction-impl`
- Assignment: `.pf/assignments/remediation-transactional-authoring-20260730.yaml`
- Primary lease: `lease-remediation-transaction-impl-20260730`
- Strict amendment lease: `lease-remediation-transaction-strict-amendment-20260730`
- Status: complete, frozen for independent review

## Delivered contract

The platform, knowledge-resource, and process authoring commands now use one
write-ahead transaction path:

1. pure preflight builds the complete byte plan and validates inputs, roots,
   parent types, collisions, schemas, and semantic postconditions;
2. entity and registry documents are staged and hash-verified;
3. entity files publish before registries;
4. any pre-commit failure restores exact pre-images in reverse order;
5. audit records, events, and process hooks run only after commit;
6. incomplete journals block the next mutation until recovery.

The affected commands require exactly one explicit mode:

- `knowledge-add-url`
- `knowledge-add-resource`
- `platform-create`
- `platform-contract-install`
- `process-create`
- `process-authoring-apply`

Neither flag and both flags fail without authoritative or audit writes.

## Platform authoring

- `platform-create` and `platform-contract-install` share the same canonical
  planner and write only
  `platform-contracts/platform.<id>/platform-contract.yaml`.
- The public `platform-contract-migrate` compatibility command is absent.
- A legacy file or a registry entry pointing at the legacy layout is an
  unsupported state and causes a preflight failure without mutation.
- Platform entities are validated before the platform-root and platform
  registries publish.

## Knowledge authoring

- Resource normalization is pure; private path registration is a planned
  registry-last write.
- The package manifest and resource index are rendered from the same in-memory
  package object and publish as one transaction.
- Added authoritative schemas for the private-resource-path and
  platform-contract-root registries.

## Process authoring

- `process-create` checks `.pf/process-forge.yaml` before constructing or
  writing session state.
- Its dry-run and apply paths share one 16-file plan: six private authoring
  files, three primary public files, and seven example files.
- `process-authoring-apply` uses the same materialization planner.
- The process definition and authoring answers are schema-validated before
  publication.
- Answer-specific `responsibility_boundaries` are materialized into the
  canonical process-definition map of role to string-list responsibilities.
- For disabled evolve, `decision.reason` is materialized to the required
  top-level `evolve.reason`; missing reasons still fail strict validation.
- Six one-shot process events and conditional hook destinations are declared
  in dry-run and execute only after commit.

## Failure evidence

The dedicated smokes inject failures after entity publication and prove that
authoritative trees and registries return to their exact pre-operation
fingerprints. They also cover:

- missing/both mode flags;
- uninitialized project roots;
- target-parent collisions;
- private-path registry rollback;
- canonical-only platform layout;
- legacy platform rejection;
- complete process dry-run destinations.

## Validation

All commands below passed on the final source state:

- `python -m py_compile tools/processforge.py`
- import plus `processforge.build_parser()`
- `python bin/pf.py --help`
- `python tools/smoke_remediation_transactional_authoring.py`
- `python tools/smoke_remediation_platform_layout_strict.py`
- `python tools/smoke_remediation_process_create_transaction.py`
- `python tools/smoke_remediation_schema_inventory.py`
- `python tools/validate-process-forge-schemas.py`
- `python tools/smoke_platform_create_include_levels.py`
- `python tools/smoke_process_authoring_writes_user_root.py`
- `python tools/smoke_process_authoring_materializes_evolve.py`
- `python tools/smoke_process_authoring_materialization_parity.py`
- `python tools/smoke_process_authoring_evolve_targeting.py`
- `python tools/smoke_process_authoring_evolve_questions.py`
- `python tools/smoke_process_definition_schema_contract.py`
- `python tools/smoke_knowledge_package_release_update_manifest.py`
- `python tools/smoke_knowledge_package_build_from_candidates.py`
- `git diff --check` for the owned product/schema/smoke/report files

## Tooling note

Serena was attempted first for symbol-aware analysis, but the project session
reported no available language server. Narrow `rg` and bounded PowerShell reads
were used as the documented fallback. No lifecycle, documentation, pack,
template, seed, checksum, or distribution work was started in this slice.
