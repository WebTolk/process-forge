# f1011-search report

## Design

- Explicit file sources now honor include/exclude patterns, including file-root resources.
- Documents are deduplicated by `(resource_id, relative_path)`.
- Refresh clears affected document and FTS rows, repairing legacy duplicate FTS state.

## Verification

- PASS — `python tools/smoke_search_source_integrity.py --root .pf/tmp/f1011-search/smoke-root-3`
- PASS — Python syntax compilation.
- BLOCKED — Existing fulltext smoke hit sandbox `PermissionError: [WinError 5]` creating its temporary fixture. No ACL investigation or retries were attempted.

## Files

- `src/processforge_core/local_resource_search.py`
- `tools/smoke_search_source_integrity.py`

The new smoke covers overlapping sources, FTS repair, filtering, file-root indexing, distinct resources, and pagination.