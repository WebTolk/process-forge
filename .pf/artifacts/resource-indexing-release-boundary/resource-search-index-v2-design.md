# Resource Search Index Design

Implementation schema: `SCHEMA_VERSION = 3`

The assignment requested normalizing the current index roughly toward `resources`, `documents`, `documents_fts`, and `index_state`. The delivered schema uses that shape.

## Tables

- `resources`: one row per indexed resource id.
- `documents`: one row per resource document or metadata navigation record.
- `documents_fts`: FTS5 table for searchable title/content fields.
- `index_state`: per snapshot authorization state, generation, status, and allowed resource ids.

## Query Flow

```text
fresh project snapshot
-> runtime resolves path_ref into request-local content_roots
-> index_status checks schema/resources/snapshot authorization
-> pf.search queries FTS rows filtered by authorized resource ids
```

## Stale Semantics

`pf.search` does not refresh. Missing/stale/degraded index state is returned as `search_status` with empty results. `search-index tick` or `refresh` performs maintenance.

## Migration

The DB is private derived state. Schema mismatch returns degraded state; `search-index tick` rebuilds the DB instead of attempting a complex migration.
