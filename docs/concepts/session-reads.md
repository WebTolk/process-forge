# Read a Ledger session

Use these MCP tools to inspect an existing Agent Ledger session. Pass its
`session_id` with each call. An explicitly configured `PF_MCP_SESSION_ID` also
binds a server process to one session. Supply `project_root` to cross-check the
project. For project context without a session, use `pf.context`.

| Tool | What you can read |
| --- | --- |
| `pf.session_context` | Current project and Work, blockers, active agents, context freshness, resources and execution readiness |
| `pf.session_chat` | The private, redacted transcript for this session. Page with `limit` (1–100) and `before` or `cursor`. Filter by `roles` when needed. |
| `pf.session_activity` | Bounded, normalized project events attributed to this session |

A fresh project snapshot can coexist with a blocked Work. Read
`execution_readiness.missing_capabilities` in the context response to see what
the Work needs. A project mismatch returns `session_project_mismatch`.
When a server is pinned to a session, a different session ID returns
`session_mismatch`.

The transcript contains messages that PF received and could attribute to this
session. Coverage depends on the client, the registered adapter and the events
it supplies. [Provider adapters](provider-adapters.md) · [Example with Codex hooks](codex-session-read.md)
