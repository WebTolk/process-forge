# PF Runtime MCP facade

`tools/pf_runtime/mcp_server.py` is a minimal stdio MCP server with one
strictly controlled initialization exception. It
requires a session identity (`--session` or `PF_MCP_SESSION_ID`) that already
exists in Agent Ledger. It does not create an MCP-specific project binding.

Available tools are `pf.project_state`, `pf.project_initialization.status`,
`pf.project_initialization.initialize`, `pf.project_initialization.repair`,
`pf.work_state`, `pf.resolve`, `pf.search`,
`pf.workplace_state`, `pf.session_context`, `pf.session_chat`, and
`pf.session_activity`. The three `pf.session_*` tools are bounded,
Ledger-authorized views; they do not read raw provider payloads. `pf.resolve` reads the selected resource metadata from
the current project's resolved context rather than asking an agent to search
the workplace or guess private paths. `pf.search` navigates only a fresh
snapshot-authorized local corpus; it never falls back to a workspace or web
scan. The two initialization write operations apply only to the Ledger-bound
project, delegate to the same Core service as CLI onboarding/repair, and
require the exact JSON value `apply: true`; otherwise they return
`apply_required`. Their responses contain structured state rather than raw
private filesystem paths; `pf.search` navigation is described separately
below.

The initialize input may include `platforms`, `specializations`, and `process`.
These are persisted by the shared Core service into the project manifest and
then resolved into the normal snapshot; the MCP facade does not compose them.

For an authorized `pf.search` match, `local_path` is a private runtime
navigation value for the matched local file. It is never written to the public
snapshot, capsules, reports, or registries. It is emitted only after Ledger
binding, fresh-snapshot validation, path-ref containment, and confirmation
that the file belongs to the result's authorized root.

`pf.work_state` also returns the declared technical-projection summary for the
Ledger-bound project. It is a read-only view of the generated
`stage-obligations` artifact; MCP does not create a second project binding or
write projection state.

MCP is not a raw-ingress API and does not expose workplace raw payloads. The
session-chat view exposes only the trusted, redacted private transcript for the
same Ledger session. See [Codex Session Read Layer](codex-session-read.md) and
[Hooks And Events](hooks-events.md) for registration and replay boundaries.
