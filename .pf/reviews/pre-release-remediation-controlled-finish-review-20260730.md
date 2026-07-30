# Review: controlled finish

- Review id: `pre-release-remediation-controlled-finish-review-20260730`
- Date: 2026-07-30
- Assignment: `remediation-controlled-finish-20260730`
- Run: `pre-release-remediation-20260730`
- Result: `pass_with_conditions`

## Status

Independent review was re-run by the root orchestrator after the report-only
review agent did not return within the bounded wait windows and was interrupted
to avoid uncontrolled background work.

This is a narrow review of the controlled finish slice only. It does not claim a
full release sign-off for ProcessForge 1.0.0.

Implementation evidence is available in:

- `.pf/artifacts/pre-release-remediation-agents/controlled-finish.md`
- `.pf/artifacts/pre-release-remediation-agents/transaction-patch-scope-reviewer.md`

## Findings

No release-blocking defect was found in the reviewed controlled-finish slice.

### Medium: final release archive gate still outstanding

The reviewed changes passed targeted local gates and public/schema checks, but
the full release package/archive sequence has not been re-run after the
transaction and schema-version changes. This remains a release-delivery gate,
not an implementation blocker for the slice.

Condition before final 1.0.0 release:

- run the full public release/archive validation sequence;
- refresh release checksums only after that final source state is accepted.

### Low: crash recovery should be promoted from probe/API coverage to a named smoke

The transaction core now verifies backup hashes and created-directory absence
before `rolled_back`, and an ad-hoc review probe covered corrupted backup and
created-directory rollback. The permanent smoke suite still mostly covers
recovery through in-process API paths. A named regression smoke that simulates
an interrupted transaction through a subprocess would make this contract harder
to regress.

Condition before final 1.0.0 release:

- add a small dedicated recovery smoke for corrupted backup / interrupted
  transaction replay, or explicitly waive it in the release checklist.

## Scope Checked

- staged platform semantic validation runs against staged overrides before
  publication;
- rollback/recovery refuses `rolled_back` when backup hash verification fails;
- rollback/recovery removes created directories only when it can verify absence;
- post-commit effects are persisted as serializable records and replayed until
  `committed_audit_complete`;
- process authoring post-commit effects no longer depend on a persisted Python
  callback;
- dry-run and apply share common preflight through `preflight_authoring_plan`;
- reusable-template public contract is `schema_version: 1` for release `1.0.0`;
- public docs/schemas/templates/tools/ADRs no longer introduce a new reusable
  template v2 contract.

## Evidence

Commands run from `D:\Dev\process-forge`:

- `python tools/smoke_remediation_transactional_authoring.py`
- `python tools/smoke_remediation_process_create_transaction.py`
- `python tools/smoke_remediation_schema_inventory.py`
- `python tools/smoke_remediation_generator_schema_alignment.py`
- `python tools/validate-process-forge-schemas.py`
- `python tools/validate-public-cleanliness.py`
- `python -m py_compile tools/processforge.py`
- `python bin/pf.py authoring-transaction-recover --help`
- `git diff --check`

All passed. `git diff --check` emitted only existing LF/CRLF normalization
warnings and no whitespace-error failure.

Additional review probes:

- direct API probe for corrupted backup recovery: returned `recovery_required`
  and did not overwrite the changed destination from a tampered backup;
- direct API probe for created-directory rollback: returned `rolled_back` and
  removed the newly created directory chain;
- grep check over `docs`, `schemas`, `templates`, `tools`, and `.pf/adr` found
  no active `schema_version: 2`, `workplaceV2`, reusable-template v2, manifest
  v2, or `v1.1.0` release contract references.

## Notes

Old v2 wording remains in earlier agent reports under
`.pf/artifacts/pre-release-remediation-agents/`. Those files are historical
audit artifacts, not active product/runtime/public contracts. The current
controlled-finish report and ADRs supersede that direction for the first public
release.

## Review Scope To Run Next

- Full release-package/archive validation.
- Permanent crash-recovery smoke, unless waived in release checklist.
