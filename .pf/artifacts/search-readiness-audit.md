# Search Readiness Audit

Status: partial

Current implementation:

- `pf.search` is read-only at query time.
- Search index refresh/rebuild belongs to maintenance commands/services.
- `project-context-refresh` runs bounded search maintenance for known projects.
- `ResourceSearchIndex.search()` returns index state rather than rebuilding.

Validated:

- `python tools/smoke_project_init_acceptance.py` confirmed FTS lifecycle:
  missing before maintenance, fresh after maintenance, stale on snapshot change.

Residual: a dedicated structured `search_readiness` MCP object was not added in
this slice.
