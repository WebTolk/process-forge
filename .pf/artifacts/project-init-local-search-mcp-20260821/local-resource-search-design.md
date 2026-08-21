# local-resource-search-design

Source: accepted `project-initialization-contract.md`; clarified during primary review.

SQLite FTS5 is a rebuildable, project-local index, never a second authority. Python's bundled SQLite 3.50.4 created and queried an FTS5 table in the active runtime, so no third-party package or vector database is needed.

## Boundary and corpus

The sole corpus is the fresh project-context snapshot and the local files explicitly resolved by its authorized resource and template records. No workspace walk, arbitrary root, Context7, web lookup, or unrelated provider is a fallback. Every candidate is containment-checked against its snapshot-authorized root and receives resource id, package/provider, type, fingerprint and canonical path.

The MCP response exposes the canonical path relative to the authorized local root together with a stable `path_ref`; public reports retain only `path_ref`. Text content is indexed only for supported bounded text files the snapshot authorizes. Binary, over-limit, unreadable and outside-root files are skipped with a reason.

## Index and lifecycle

The private runtime cache stores documents/metadata and an FTS5 table. Its manifest pins snapshot id/checksum plus resource fingerprints. Build or rebuild only when that manifest is absent or differs; invalidate for stale/broken snapshots, checksum/fingerprint drift, stale marker or missing files. Empty authorized corpora produce a valid `empty` index.

Search accepts `query`, `limit` and Joomla-style `limitstart`; `offset` is an alias only when `limitstart` is absent, otherwise conflicting values fail. It returns bounded navigation results, total/next cursor facts, match rationale and provenance—not content dumps. Ranking remains SQLite FTS5's local default and is deliberately not presented as a solved relevance system.

## Fail-closed behaviour

Missing, stale or broken snapshot; absent cache; invalid pagination; unauthorized roots; and malformed FTS syntax return stable errors/statuses. The index cannot refresh the snapshot or broaden authorization on read.
