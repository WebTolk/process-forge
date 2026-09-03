# Resource Indexing Implementation Report

## Changed Files

- `src/processforge_core/local_resource_search.py`
- `tools/processforge.py`
- `tools/pf_runtime/session_read.py`
- `tools/smoke_project_init_local_search_mcp.py`
- `tools/smoke_resource_indexing_policy_acceptance.py`
- `schemas/resource-indexing.schema.json`
- Resource/schema/docs files listed in Git diff.

## Implementation

- Added resource-oriented SQLite schema v3.
- Added normalization for explicit `indexing` policies and legacy `index_policy` compatibility.
- Removed hidden query-time build/rebuild from `search()`.
- Kept bounded maintenance in `maintenance_tick()`.
- Updated session context readiness to resolve `path_ref` in the same request-local way as MCP `pf.search`.
- Added release-test coverage for indexing-policy acceptance.

## Validation

- Compile PASS.
- Schema validation PASS.
- Public cleanliness PASS.
- Checksum inventory updated and PASS.
- Focused search/MCP/privacy smokes PASS.
