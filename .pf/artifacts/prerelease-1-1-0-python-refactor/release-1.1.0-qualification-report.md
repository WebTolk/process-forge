# ProcessForge 1.1.0 Qualification Report

Date: 2026-08-23
Status: PASS

## Source Gates

- PASS: schema validation.
- PASS: public cleanliness.
- PASS: checksum inventory before version/refactor edits.
- PASS: release-check before version/refactor edits.
- PASS: explicit py_compile before refactor.
- PASS: selected critical smokes except clean-source provenance.

## Gate Closure

- DONE: Refresh checksum inventory.
- DONE: Run source gates after VERSION/CHANGELOG/refactor edits.
- DONE: Repair project-context false blocker and create assignment capsule.
- DONE: Commit source baseline: `49695f7`.
- DONE: Run clean-source public `release-test`.
- DONE: Build 1.1.0 archive.
- DONE: Run quick and full extracted archive tests.
- DONE: Run clean install acceptance against archive.
- DONE: Run in-place update acceptance against archive.
- DONE: Run independent code and release reviews.

## Post-Edit Source Gate Results

- PASS: explicit Python compile.
- PASS: `smoke_process_catalog_not_implicit_execution_route`.
- PASS: `smoke_project_init_local_search_mcp`.
- PASS: `smoke_resource_indexing_policy_acceptance`.
- PASS: `smoke_context_freshness_vs_execution_readiness`.
- PASS: `smoke_project_init_acceptance`.
- PASS: `smoke_core_update_manifest`.
- PASS: `smoke_update_stage_verify_apply_file_provider`.
- PASS: `validate-process-forge-schemas`.
- PASS: `validate-public-cleanliness`.
- PASS: `validate-process-forge-checksums --write`.
- PASS: `validate-process-forge-checksums --check`.

## Release Package

- Archive: `dist/processforge.zip`.
- Manifest: `dist/processforge.manifest.json`.
- Version: `1.1.0`.
- Files: `869`.
- Size: `1280633` bytes.
- SHA256:
  `fd4c9948de1270a2b836c19796b6882ab994ec61dde854a44403f949661f43dc`.
- Manifest source commit:
  `49695f7f0a156f21382a91c5da44dffab5164d7c`.

## Release Gates

- PASS: full public `release-test --public`, elapsed `943.73s`.
- PASS: `release-archive-test --extracted-test quick`.
- PASS: `release-archive-test --extracted-test full`, inner extracted
  `release-test` elapsed `868.49s`.
- PASS: clean install acceptance.
- PASS: in-place update acceptance with compatibility note.
- PASS: installed RC MCP JSON-RPC proof for `pf.session_context`, `pf.search`,
  and `pf.resolve`.
