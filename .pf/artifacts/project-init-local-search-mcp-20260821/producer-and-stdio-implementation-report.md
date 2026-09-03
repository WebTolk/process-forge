# Snapshot producer and stdio MCP implementation

Implemented a public metadata-only `local_search_resources` snapshot field from resolved available knowledge resources. Entries retain ids, package/kind, `path_ref`, status and policies; they intentionally contain no resolved filesystem path or content root.

Validation: `py_compile` for the CLI and smoke passed; the FTS5 smoke and `git diff --check` passed. The Spark-produced stdio fixture recipe is retained at `stdio-fixture-inventory.md` and has been independently checked against the current MCP binding/error code paths.

Remaining implementation: execute that fixture as an automated subprocess smoke and add private runtime-only `path_ref` resolution so metadata-only records can authorise content indexing without making paths public.

## Automated stdio proof

The fixture is now automated in `tools/smoke_project_init_local_search_mcp.py`: it initializes a temporary workplace and two projects, checks in a Ledger session to the first project, starts the stdio MCP subprocess, verifies `initialize`, checks `tools/list` for `pf.search`, and asserts `session_project_mismatch` for the second project. The smoke passes directly.

The private runtime-only `path_ref` content-resolution bridge remains a separate follow-up.
