# Search Index Runtime Policy

Run: `operational-hardening-search-update-20260822`

## Policy

- On PF-owned resource-management mutation: mark existing workplace index scopes `stale`.
- On external filesystem mutation: detect by bounded fingerprint reconciliation in `search-index tick`.
- On missing/stale scope: refresh only the current project snapshot scope.
- On schema-degraded derived DB: rebuild the derived DB.
- On `fts5_unavailable`: report degraded capability; do not hide it with fallback semantics.
- `pf.search` must not perform background indexing or hidden global search.

## Cadence Recommendation

Until production corpus timings exist:

- run `tick` after lifecycle mutations;
- run `tick` at session/bootstrap boundaries;
- allow operator/manual `search-index tick`;
- avoid hardcoded aggressive background polling.

## Future Work

Move from scattered lifecycle helper calls to a Runtime-owned scheduler consuming dirty events.
