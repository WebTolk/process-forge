# Private search path-ref bridge

The snapshot producer now preserves only structured, public `path_ref` metadata. During a Ledger-bound `pf.search` request, MCP copies the snapshot and resolves those refs through the existing Core resolver into transient `content_roots`. The roots are neither written into the snapshot nor returned in search results.

Verification: `py_compile` for CLI/MCP passed; automated FTS5 and stdio MCP smoke passed; `git diff --check` passed.
