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

## Automatic maintenance triggers

ProcessForge runs the same bounded maintenance pass from lifecycle commands that can change the authorized search scope:

- `workplace-init` creates the private search runtime report and ticks any already-known onboarded projects under the workplace.
- `project-onboard`, `project-init-repair`, and `project-context-refresh` tick the current project after writing a fresh project context snapshot.
- resource authoring commands such as `knowledge-add-url`, `knowledge-add-resource`, `knowledge-index-refresh`, `template-create`, `tool-register`, `mcp-register`, `platform-create`, and `platform-contract-install` tick known onboarded projects under the workplace.
- `update-apply` and `update-rollback` mark impacted project snapshots stale first, then run maintenance; stale projects are skipped until `project-context-refresh` creates a fresh snapshot.

The automatic pass writes a private derived report:

```text
<workplace>/runtime/search/latest-maintenance.yaml
```

It is intentionally bounded to known ProcessForge projects and never builds a global workplace index. When a project context is stale, ProcessForge reports `SEARCH_INDEX_SKIPPED` with the required next action instead of rebuilding against obsolete authorization data.

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

This implementation keeps the index derived and rebuildable, uses SQLite FTS5, and avoids hidden global search. Lifecycle-triggered maintenance covers first-run, project context refresh, resource authoring, and update apply/rollback paths. Crash recovery states beyond safe rebuild and production-scale benchmark coverage remain future slices.
