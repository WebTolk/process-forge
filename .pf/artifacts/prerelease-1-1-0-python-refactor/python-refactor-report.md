# Python Refactor Report

Date: 2026-08-23

## Slice

Added `ResourceSearchIndex` to
`src/processforge_core/local_resource_search.py`.

## Behavior

No public behavior, file format, CLI command, MCP tool, or JSON/YAML contract is
intended to change. Existing module-level functions remain compatibility APIs.

## Adapter Changes

- `tools/processforge.py` search-index commands now use `ResourceSearchIndex`.
- `tools/pf_runtime/mcp_server.py` `pf.search` now uses `ResourceSearchIndex`.
- `tools/pf_runtime/session_read.py` session search readiness now uses
  `ResourceSearchIndex`.

## Measurement

- `tools/processforge.py` line count before slice: about 24240 lines.
- Refactor did not target line-count reduction; it moved ownership of search
  index state from repeated adapter calls to a single Core service object.
- The state tuple `{project_root, snapshot, workplace_root}` now has one
  explicit owner for status/refresh/rebuild/dirty/tick/search operations.

## Compatibility

- Existing imports of `build_index`, `rebuild_index`, `index_status`,
  `mark_index_dirty`, `maintenance_tick`, and `search` remain valid.

## Post-Edit Validation

- PASS: `python -m py_compile` for `tools/processforge.py`,
  Runtime adapter files, the new smoke, and `src/processforge_core/**/*.py`.
- PASS: `tools/smoke_project_init_local_search_mcp.py`.
- PASS: `tools/smoke_resource_indexing_policy_acceptance.py`.
- PASS: `tools/smoke_context_freshness_vs_execution_readiness.py`.
- PASS: `tools/smoke_process_catalog_not_implicit_execution_route.py`.
- PASS: `tools/smoke_project_init_acceptance.py`.
- PASS: `tools/smoke_core_update_manifest.py`.
- PASS: `tools/smoke_update_stage_verify_apply_file_provider.py`.
- PASS: schema validation, public cleanliness, checksum write, checksum check.
