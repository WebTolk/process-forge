# MCP session binding design

1. The hook session is checked in to the existing Agent Ledger for a project.
2. `pf.session_*` receives the session id, finds exactly that Ledger presence, resolves its project, and verifies the stored project id.
3. Optional `project_root` is resolved only as a consistency assertion; a different project produces `session_project_mismatch`.
4. Only then does the read layer load transcript or normalized project events.

No MCP session table, current-session fallback, or raw provider identity is an authority source. Missing, unknown, unrouted and invalid sessions fail closed with stable error codes.
