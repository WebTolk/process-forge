# Resource Search Index

ProcessForge exposes local resource search through three separate layers:

- the project context snapshot is the authorization boundary;
- the SQLite search index is private, derived, and rebuildable;
- MCP is only a query adapter.

The search index is stored under the workplace runtime directory:

```text
<workplace>/runtime/search/local-resource-search.sqlite
```

The index can contain multiple project snapshot scopes, but a query is always filtered by the active Ledger session, bound project, and fresh project snapshot. `pf.search` must not fall back to the full workplace, other projects, home directories, Context7, or the web.

## CLI

Operators can inspect and maintain the index without MCP:

```bash
python bin/pf.py search-index status --project-root <project> --workplace <workplace>
python bin/pf.py search-index refresh --project-root <project> --workplace <workplace>
python bin/pf.py search-index rebuild --project-root <project> --workplace <workplace>
python bin/pf.py search-index doctor --project-root <project> --workplace <workplace>
python bin/pf.py search-index tick --project-root <project> --workplace <workplace>
```

`status` is read-only. `refresh` updates the current project snapshot scope. `rebuild` removes the derived DB and builds it again for the current project snapshot scope.

`status --verify-files` performs an explicit file fingerprint check for the current snapshot scope. It can mark the index `stale` when authorized files changed outside ProcessForge.

`tick` is one bounded maintenance pass suitable for Runtime or operator scheduling. It verifies fingerprints by default and refreshes only when the scope is missing or stale. MCP calls do not perform this verification on every query.

## Runtime and MCP contract

`pf.search` returns navigation-oriented results, not generated answers. The payload includes:

- `search_status`
- `index_generation`
- `total`
- `limit`
- `offset`
- `items` / `results`

`pf.session_context` includes compact search readiness:

```yaml
search:
  status: fresh
  generation: <index-generation>
  stale: false
```

The index stores private resolved paths only as runtime data. Public project snapshots and public artifacts must keep `path_ref` references instead of machine-local absolute paths.

## Current limits

This implementation keeps the index derived and rebuildable, uses SQLite FTS5, and avoids hidden global search. A bounded maintenance tick is available for Runtime/operator scheduling. Event-based dirty marking, crash recovery states beyond safe rebuild, and production-scale benchmark coverage remain future slices.
