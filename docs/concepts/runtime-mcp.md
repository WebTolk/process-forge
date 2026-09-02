# PF Runtime MCP facade

`tools/pf_runtime/mcp_server.py` is a minimal stdio MCP server. It is
host-owned: Codex starts the Python process from Codex MCP configuration and
owns the stdin/stdout pipes. It is not registered as a Windows scheduled task or
detached background service.

Garage read tools accept an explicit `project_root` and do not require a session identity,
hooks, daemon, Ledger event, Director process, or chat transcript. Session and
Forge tools still require a session identity (`--session`, `PF_MCP_SESSION_ID`,
or `session_id`) that already exists in Agent Ledger.

Generic project initialization is host-agnostic. It does not install Codex
hooks or start Runtime infrastructure. Codex hook telemetry is an optional,
explicit host integration for operators who need Forge session capture.

Available tools are `pf.context`, `pf.project_state`, `pf.project_initialization.status`,
`pf.project_initialization.initialize`, `pf.project_initialization.repair`,
`pf.work_state`, `pf.work.state`, `pf.work.start`, `pf.work.transition`, `pf.resolve`, `pf.search`,
`pf.workplace_state`, `pf.session_context`, `pf.session_chat`, and
`pf.session_activity`. `pf.context`, `pf.project_state`,
`pf.project_initialization.status`, `pf.work_state`, `pf.work.state`, `pf.resolve`, and
`pf.search` are Garage reads and can run from `project_root`. `pf.work.start`
and `pf.work.transition` are Garage-scoped governed mutations that can also run
from `project_root`. The
three `pf.session_*` tools are bounded, Ledger-authorized views; they do not read raw
provider payloads. `pf.resolve` reads the selected resource metadata from
the current project's resolved context rather than asking an agent to search
the workplace or guess private paths. `pf.search` navigates only a fresh
snapshot-authorized local corpus; it never falls back to a workspace or web
scan. The two initialization write operations are governed maintenance actions,
delegate to the same Core service as CLI onboarding/repair, and require the
exact JSON value `apply: true`; otherwise they return
`apply_required`. Their responses contain structured state rather than raw
private filesystem paths; `pf.search` navigation is described separately
below.

`pf.work.start` is the preferred transition from Garage understanding to
governed work. The agent supplies only a non-empty `objective`. ProcessForge
validates and pins the process definition, selects its declared initial stage,
creates or reuses the Run and Assignment, and returns the current work state.
The agent then uses `pf.work.state` and `pf.work.transition(outcome, evidence)`;
the next stage is never a caller input. A session id may
link telemetry, but session availability does not change `mode: garage` to
`mode: forge`.

Session-scoped tool failures return stable machine-readable error codes. For
`missing_session`, the error payload also includes a bounded remediation object:
use the Garage tools when the requested operation does not need a Ledger
session, or ask an operator to verify the configured host integration before
retrying a Forge-only tool. An ordinary project agent must not install hooks or
start Runtime as remediation. Manual `session-start` remains an operator
diagnostic fallback and must not be used to invent production session ids.

The initialize input may include `platforms`, `specializations`, and `process`.
These are persisted by the shared Core service into the project manifest and
then resolved into the normal snapshot; the MCP facade does not compose them.

For an authorized `pf.search` match, `local_path` is a private runtime
navigation value for the matched local file. It is never written to the public
snapshot, capsules, reports, or registries. It is emitted only after
project-snapshot authorization, fresh-snapshot validation, path-ref containment,
and confirmation that the file belongs to the result's authorized root.

`pf.work_state` is retained as a compatibility alias for `pf.work.state`.
The state is derived from canonical Run and Assignment files plus the pinned
Process definition; technical projector facts remain declaration-driven.

MCP is not a raw-ingress API and does not expose workplace raw payloads. The
session-chat view exposes only the trusted, redacted private transcript for the
same Ledger session. See [Codex Session Read Layer](codex-session-read.md) and
[Hooks And Events](hooks-events.md) for registration and replay boundaries.

Codex host registration can be inspected, installed, or removed with
`python bin/pf.py codex-mcp status|install|remove --workplace <workplace>`.
Install and remove are dry-run by default and require `--apply` to change Codex
configuration. Restart or reload Codex after registration changes.
