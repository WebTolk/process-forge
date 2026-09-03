# Search Index Lifecycle Audit

Run: `operational-hardening-search-update-20260822`

## Findings

- Authorization remains `project context snapshot -> local_search_resources -> scope_key`.
- The derived DB lives at `runtime/search/local-resource-search.sqlite` under the workplace.
- External file add/change/delete is detected by `index_status(... verify_files=True)` through document fingerprint comparison.
- `search-index tick` performs bounded maintenance: missing/stale scopes refresh; schema-degraded derived DB state rebuilds.
- PF-owned resource-management events now mark existing workplace index scopes `stale`, so correctness no longer depends only on each CLI command remembering to call a maintenance helper.
- `pf.search` remains a query adapter and does not reconcile fingerprints on every query.

## Defect Found And Fixed

Old FTS rows survived refresh because scope deletion removed `documents` rows but did not reliably remove FTS rows for the same scope. `_delete_scope()` now deletes `documents_fts` by `scope_key` before deleting `documents`.

## Residual Risks

- Runtime periodic scheduling is documented as policy, but no long-lived daemon scheduler is implemented in this slice.
- Production-scale benchmark coverage remains pending.
