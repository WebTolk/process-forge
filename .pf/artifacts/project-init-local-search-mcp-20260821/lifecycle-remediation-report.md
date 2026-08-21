# FTS5 lifecycle remediation

The search cache now reports `stale` when an existing index is rebuilt for a changed snapshot checksum, preserves `empty` for a successful empty build, and normalizes filesystem/SQLite opening failures to `search_unavailable`.

`smoke_project_init_local_search_mcp.py` now proves the `current` result followed by the observable `stale` transition for a changed snapshot id. `py_compile`, smoke and `git diff --check` passed.

Still pending: public metadata producer plus private runtime path resolution, and a real Ledger-backed stdio MCP fixture.
