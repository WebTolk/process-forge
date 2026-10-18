# PF Runtime MCP facade

For a read-only terminal view of the existing workplace service, see the
[local Runtime monitor](runtime-monitor.md).

For exact Work/context resource selectors, material verification and current
authorization, see [Work-scoped resource reads](work-resources.md).

For the loaded CLI/MCP action catalogue, exact arguments and additional native
worker/session operations, see [supported action discovery](action-discovery.md).

For bounded request logging, privacy, profiles and local exports, see
[optional diagnostics](diagnostics.md). MCP stdout remains JSON-RPC only.

`tools/pf_runtime/mcp_server.py` is a minimal stdio MCP server. It is
host-owned: Codex starts the Python process from Codex MCP configuration and
owns the stdin/stdout pipes. It is not registered as a Windows scheduled task or
detached background service.

The optional **pf-app-server** is the separate workplace Runtime service for
scheduling and orchestration. This stdio facade calls shared Core services;
Garage context and governed Work do not require a running app-server. Use the
existing CLI when no MCP connection is available. See
[Garage Core](garage-core.md) and [requirements](../requirements.md).

## Implementation reference: stdio transport

At startup, the server configures standard stdin and stdout text codecs as UTF-8,
independently of the locale and `PYTHONIOENCODING`. Streams already using UTF-8
keep their codec, including input that was read before startup. Unicode path
code points are preserved; filenames are not transliterated or normalized.
Embedded text streams without `reconfigure` retain their behavior and ownership.
A non-UTF-8 input stream must be configured before reading; any provided
`reconfigure` must accept the standard `encoding` and `errors` keywords.
Configuration failures propagate.

The native transport validates JSON-RPC 2.0 envelopes and advertised tool
argument schemas before dispatch. Parse errors, invalid requests, and invalid
parameters return distinct protocol errors. Notifications have no response,
including when dispatch fails; an explicit null `id` remains a request.

## Use the project and Work tools

Garage read tools accept an explicit `project_root` and do not require a session identity,
hooks, daemon, Ledger event, Director process, or chat transcript. Session and
Forge tools still require a session identity (`--session`, `PF_MCP_SESSION_ID`,
or `session_id`) that already exists in Agent Ledger.

Generic project initialization is host-agnostic. It does not install Codex
hooks or start Runtime infrastructure. Codex hook telemetry is an optional,
explicit host integration for operators who need Forge session capture.

Available tools are `pf.context`, `pf.project_state`, `pf.project_initialization.status`,
`pf.project_initialization.initialize`, `pf.project_initialization.repair`,
`pf.work_state`, `pf.work.state`, `pf.work.start`, `pf.work.transition`,
`pf.continuation.create`, `pf.continuation.status`, `pf.continuation.resume`,
`pf.work.cancel`,
`pf.work.search`, `pf.work.resolve`, `pf.resolve`, `pf.search`,
`pf.workplace_state`, `pf.session_context`, `pf.session_chat`, and
`pf.session_activity`. The additional `pf.actions.*`, `pf.runtime_driver.*`,
`pf.worker.*`, `pf.session.heartbeat` and `pf.chat.record` tools are specified in
[action discovery](action-discovery.md). The complete actual registry is available
through `pf.actions.list`; support and current permission remain separate facts.
`pf.context`, `pf.project_state`,
`pf.project_initialization.status`, `pf.work_state`, `pf.work.state`, `pf.resolve`, and
`pf.search` are Garage reads and can run from `project_root`. The Work read
routes additionally require exact `run_id`, `assignment_id`, and `context_id`;
see [Work-scoped resource reads](work-resources.md). `pf.work.start`
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
governed work. The agent supplies a non-empty `objective` and may also supply
`process_id` when the project authorizes more than one process. If selection is
ambiguous, ProcessForge returns `process_choice_required` candidates and the
caller must choose one of them; `default` is a recommendation, not an implicit
selection. ProcessForge validates and pins the process definition, selects its
declared initial stage, creates or reuses the Run and Assignment, and returns
the current work state. The agent then uses `pf.work.state` and
`pf.work.transition(outcome, evidence)`; the next stage is never a caller
input. A session id may link telemetry, but session availability does not
change `mode: garage` to `mode: forge`.

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

For continuation, retain the returned Run/Assignment/context identity and check
it against durable handoff evidence after reconnect. A generic current-Work
fallback can select another unfinished Run after completion; it is not proof
that it selected the intended work. Session identity does not replace a Work
selector. Work reads intersect pinned grants, current authorization and stage
restrictions without silently migrating older capsules.

The tool list above describes the current source. An installed MCP process
may expose an older set; compare its advertised tools and loaded build before
claiming source/host parity. Source subprocess tests, installed reconnect tests,
and checks through an application's actual connected MCP are separate evidence.

`pf.work_state` is retained as a compatibility alias for `pf.work.state`.
The state is derived from canonical Run and Assignment files plus the pinned
Process definition; technical projector facts remain declaration-driven.

MCP is not a raw-ingress API and does not expose raw hook payloads. The
session-chat view exposes only the trusted, redacted private transcript for the
same Ledger session. See [Codex Session Read Layer](codex-session-read.md) and
[Hooks And Events](hooks-events.md) for registration and replay boundaries.

Codex host registration can be inspected, installed, or removed with
`python bin/pf.py codex-mcp status|install|remove --workplace <workplace>`.
Install and remove are dry-run by default and require `--apply` to change Codex
configuration. Restart or reload Codex after registration changes.

Local operator commands are also available as `pf server` or
`python bin/pf-server.py`: start, run, status, stop and restart. Guarded stop
requires current worker/request/scheduler idleness and a compatible owner;
`--force` explicitly bypasses that guard. Server status is the bounded read-only
[monitor](runtime-monitor.md) projection. These commands control the workplace
Runtime, not the host-owned MCP stdio process; updating Core on disk does not
reload a connected host.

## Implementation reference: Runtime HTTP request bodies

The existing loopback Runtime POST adapter accepts a JSON object within a
1 MiB byte limit. `Content-Length` must contain ASCII decimal digits, with
surrounding whitespace allowed. Missing, empty or zero length retains the
existing empty-object behavior. Invalid or excessive lengths are rejected
before reading; a shorter body is rejected before JSON parsing or dispatch.
JSON numbers must remain finite after float conversion: `NaN`, `Infinity`,
`-Infinity` and numeric overflow are rejected, including nested values.
Finite numbers, integers and strings keep their normal JSON behavior.

These failures use the existing HTTP 400 error mapping. The parser reports
`invalid Content-Length`, `incomplete request body` or
`request JSON numbers must be finite`; the existing oversize and non-object
errors remain unchanged. Bearer authorization and stopping checks precede
body reading. Run `python tools/smoke_runtime_http_body.py` for focused inert
reader and isolated HTTP checks; this does not qualify an installed Runtime.
