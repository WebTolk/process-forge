# Search Resolver Consistency

- Result: PASS
- Confirmed defect: Garage search, search-index maintenance, and session context resolved authorized `path_ref` values through divergent runtime-snapshot implementations.
- Impact: a Garage query could replace an index row with the same snapshot scope but a different authorized-resource set, after which `pf.session_context` reported the index as stale.
- Fix: `local_search_runtime_snapshot` and `pf_runtime.session_read` now use `processforge_core.garage.snapshot_with_resolved_search_roots`.
- Regression: `smoke_project_init_local_search_mcp.py` now reports repair and search state on failure.

## Verification

- `python -m py_compile tools/processforge.py tools/pf_runtime/session_read.py`: PASS
- `python tools/smoke_project_init_local_search_mcp.py`: PASS in source and isolated 1.2.1 candidate
- `python tools/smoke_garage_session_enhanced.py`: PASS in source and candidate
- `python tools/smoke_garage_no_hooks_sessionless.py`: PASS in source and candidate
- `python tools/smoke_fulltext_article_indexing.py`: PASS in source and candidate
