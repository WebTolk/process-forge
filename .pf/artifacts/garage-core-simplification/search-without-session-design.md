# Search Without Session Design

Generated: 2026-08-24 14:45 +04

## Target

`pf.search(project_root, query)` works without Ledger session.

## Flow

1. Resolve project root and `.pf`.
2. Run context check.
3. If snapshot is fresh or safely refreshable, use current snapshot.
4. Resolve `path_ref` entries into request-local private roots.
5. Run bounded search preparation through `maintenance_tick()` when index is
   missing or stale.
6. Execute pure `search()`.
7. Return only snapshot-authorized matches.

## Readiness Mapping

- `ready`: fresh index with searchable documents.
- `empty`: fresh index but no authorized resources or documents.
- `stale`: index/snapshot requires maintenance or operator decision.
- `blocked`: broken snapshot, invalid project, missing resource authorization,
  or unavailable SQLite/FTS.

## Compatibility

Existing `pf.search` remains the tool name. The behavior changes only for
missing session: it now uses `project_root` as the Garage authority.
