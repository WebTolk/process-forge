# Resource Index Implementation Report

Run: `stable-mcp-resource-index-implementation-20260822`
Task: `stable-mcp-resource-index-first-slice-20260822`

## Implemented

- Moved MCP local resource search to a workplace-level derived SQLite DB path:
  - `<workplace>/runtime/search/local-resource-search.sqlite`
  - project-local DB path remains only as a backward-compatible direct-library fallback.
- Added SQLite schema version `2` with:
  - `meta`
  - `index_state`
  - `documents`
  - `documents_fts`
- Added snapshot-scope filtering inside the DB through `scope_key`.
- Added read-only index status primitive.
- Added refresh and rebuild primitives.
- Added FTS5 capability probing.
- Preserved snapshot authorization: the search module still receives only caller-supplied snapshot resources, and MCP resolves private `path_ref` roots only in request-local runtime memory.
- Extended `pf.search` payload with:
  - `index_generation`
  - top-level `total`, `limit`, `offset`
  - `items` alias while preserving existing `results` and `page`.
- Added compact `search` readiness to `pf.session_context`.
- Added CLI:
  - `search-index status`
  - `search-index refresh`
  - `search-index rebuild`
  - `search-index doctor`
- Updated smoke coverage for:
  - new `missing/fresh/stale` lifecycle states;
  - workplace-level DB path created by MCP/CLI;
  - CLI status/refresh/doctor;
  - `pf.session_context.search`.
- Added EN/RU docs:
  - `docs/concepts/resource-search-index.md`
  - `docs/ru/concepts/resource-search-index.md`

## Validation

- `python -m py_compile tools/processforge.py tools/pf_runtime/mcp_server.py tools/pf_runtime/session_read.py src/processforge_core/local_resource_search.py tools/smoke_project_init_local_search_mcp.py tools/smoke_project_init_acceptance.py`
- `python tools/processforge.py search-index --help`
- `python tools/smoke_project_init_local_search_mcp.py`
- `python tools/smoke_project_init_acceptance.py`

## Not Yet Complete From Master Prompt

The full master prompt remains larger than this first implementation slice. These items still need separate slices:

- Runtime periodic maintenance and scheduling.
- Dirty marking from PF writes/registry changes.
- True incremental refresh based on file fingerprints instead of scope rebuild.
- Crash/restart recovery state beyond safe derived rebuild.
- Production-scale benchmark report.
- Full acceptance fixture with A/B/C resource visibility matrix.
- Conversation deferred/replay remediation finalization if not already closed by the separate Codex capture run.
- Independent architecture and code reviews.
- Release/archive validation for the full combined stage.
