# PF Runtime MCP facade

`tools/pf_runtime/mcp_server.py` is a minimal read-only stdio MCP server. It
requires a session identity (`--session` or `PF_MCP_SESSION_ID`) that already
exists in Agent Ledger. It does not create an MCP-specific project binding.

Available tools are `pf.project_state`, `pf.work_state`, `pf.resolve`,
`pf.workplace_state`, `pf.session_context`, `pf.session_chat`, and
`pf.session_activity`. The three `pf.session_*` tools are bounded,
Ledger-authorized views; they do not read raw provider payloads. `pf.resolve` reads the selected resource metadata from
the current project's resolved context rather than asking an agent to search
the workplace or guess private paths.

`pf.work_state` also returns the declared technical-projection summary for the
Ledger-bound project. It is a read-only view of the generated
`stage-obligations` artifact; MCP does not create a second project binding or
write projection state.

MCP is not a raw-ingress API and does not expose workplace raw payloads. The
session-chat view exposes only the trusted, redacted private transcript for the
same Ledger session. See [Codex Session Read Layer](codex-session-read.md) and
[Hooks And Events](hooks-events.md) for registration and replay boundaries.
