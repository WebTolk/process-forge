# Local ProcessForge Runtime, Agent Events, And Unified MCP Interface

- date: 2026-08-13
- run: `pf-runtime-mcp-20260813`
- assignment: `runtime-mcp-architecture-report`
- scope: architecture report before PoC implementation
- implementation status: not started

## Decision Summary

ProcessForge should add a small optional local Runtime service as an interface layer over existing PF Core files and functions. The service must not become a second ProcessForge engine. The CLI remains the authoritative execution path and must keep working when the service is stopped.

Recommended PoC shape:

- foreground local service process, started explicitly for one user/workplace;
- loopback HTTP API on `127.0.0.1` with a random bearer token stored in private runtime state;
- thin agent adapters that normalize hook payloads into existing ProcessForge event envelopes;
- one MCP server facade that exposes selected project/work-state tools by calling PF Core functions or CLI-equivalent wrappers;
- one projection artifact generated from durable `.pf/runtime/events/events.ndjson`.

## A. What Can Be Reused

Existing reusable PF Core surfaces:

- Event envelope and append path: `processforge_event`, `append_process_event`, `emit_process_event`, `validate_event_object`, `command_events_validate` in `tools/processforge.py`.
- Durable event stream: `.pf/runtime/events/events.ndjson`.
- Hook configuration and dispatch: `.pf/hooks.yaml`, `validate_hooks_config`, `selected_hooks`, `dispatch_hooks`, `hook_delivery_payload`, `write_hook_result`.
- Hook outbox/results paths: `.pf/runtime/hooks/outbox/` and `.pf/runtime/hooks/results/`.
- Session telemetry: `.pf/runtime/sessions/`, `.pf/runtime/telemetry/`, event vocabulary in `docs/concepts/session-telemetry.md`.
- Project context: `project_context_check_result`, `build_project_context_snapshot`, `resolve_project_parameters`, `resolve_specialization_context`, `command_context_resolve`.
- Agent presence and ledger: `agent-checkin`, `agent-heartbeat`, `agent-checkout`, `agent-status`, `workplace_agent_ledger_path`, `workplace_agent_presence_dir`.
- Runtime worker model: `runtime_driver_*`, `worker-run prepare/start/status/stop/collect`, `.pf/runtime/agent-runs/`.
- MCP/tool registry model: `command_mcp_register`, `command_tool_register`, workplace `registries/mcp.yaml` and `registries/tools.yaml`.
- Path/resource resolution: `command_path_resolve` and existing knowledge/template registries.

Reusable policy boundaries:

- `docs/concepts/runtime-model.md` states that PF uses short-lived CLI commands by default and does not require a daemon.
- `docs/concepts/hooks-events.md` states that the current runtime writes local files, while network delivery and long-running processing are outside the core runtime.
- `.pf/hooks.yaml` already defaults to `network_send_enabled: false`, outbox-first delivery, secret refs, and metadata-only chat.

Conclusion: the service can reuse the file-first runtime, event model, context resolver, agent ledger, runtime driver state, and registry model. It should add adapters and serving code, not duplicate lifecycle decisions.

## B. Runtime Location

Recommended code layout for the PoC:

- `tools/pf_runtime/service.py`: local service process, request routing, token validation, graceful shutdown.
- `tools/pf_runtime/events.py`: adapter payload normalization into existing `processforge_event` envelopes.
- `tools/pf_runtime/projections.py`: rebuildable projections from `.pf/runtime/events/events.ndjson`.
- `tools/pf_runtime/mcp_server.py`: unified MCP facade calling PF Core functions.
- `tools/pf_runtime/adapters/`: one file per agent family only for input mapping.
- `schemas/pf-runtime-agent-event.schema.json`: optional adapter input schema, separate from the existing ProcessForge event envelope.

Recommended private runtime state:

- workplace-level service state: `<workplace>/runtime/pf-runtime/service.json`, `token`, `pid`, `port`, `started_at`;
- project-level durable facts: existing `.pf/runtime/events/events.ndjson`;
- project-level generated projection: `.pf/artifacts/pf-runtime-mcp-20260813/command-history.md` for the PoC, later `.pf/artifacts/projections/command-history.md`.

The service may cache open project handles in memory, but every authoritative fact must be recoverable from project/workplace files.

## C. Service Lifecycle

Lifecycle:

1. `runtime serve` starts a foreground service for one workplace.
2. Service resolves the workplace, creates private runtime directory, generates or rotates an auth token, binds to `127.0.0.1`.
3. Service exposes `/status`, `/event`, and an MCP transport endpoint or stdio MCP process.
4. Agent hooks send events to `/event`; MCP clients call tools through the MCP facade.
5. Service appends normalized events through `append_process_event`, then rebuilds or updates projections.
6. On restart, service reads existing event streams and service state; no project truth is taken from memory.
7. On shutdown, service removes or marks pid state stale, but does not delete events/projections.

PoC should not install a Windows Service, scheduled task, or always-on daemon. Those can be added later after operator approval and security review.

## D. IPC

Recommended PoC IPC: loopback HTTP bound only to `127.0.0.1`.

Reasoning:

- Claude Code hooks support shell command handlers and HTTP endpoints.
- Gemini CLI hooks can run commands that read JSON from stdin and write JSON decisions to stdout; a small command shim can POST to loopback.
- Codex CLI hooks appear to be an evolving/experimental surface in public GitHub issues and are not documented as a stable universal agent-app feature.
- Kimi CLI hook support was found as a feature discussion/proposal, not confirmed as a stable API.

Loopback HTTP gives one simple target for all adapters. It is weaker than OS-level named pipes for local authorization, so token auth, localhost-only binding, path allowlisting, payload limits, and no command execution from payloads are mandatory.

Later alternative: Windows named pipe plus Unix domain socket. That is more secure by OS boundary, but increases platform-specific code and adapter complexity.

## E. Event Schema

The Runtime should not replace `schemas/event-envelope.schema.json`. It should accept agent-specific input, normalize it, then write an existing ProcessForge event envelope.

Minimal normalized input:

```json
{
  "schema_version": 1,
  "event_id": "agent-generated-or-hash",
  "event_type": "agent.command.completed",
  "source": {
    "adapter": "codex",
    "agent": "codex-cli",
    "session_id": "..."
  },
  "project_root": "D:/Dev/process-forge",
  "cwd": "D:/Dev/process-forge",
  "run_id": "optional",
  "task_id": "optional",
  "payload": {
    "command": "optional sanitized command",
    "exit_code": 0,
    "files": []
  },
  "raw": {
    "hash": "sha256:...",
    "stored": false
  }
}
```

PF envelope mapping:

- `event_type`: map adapter events to a controlled ProcessForge namespace, for example `agent.command.completed`, `agent.file.changed`, `agent.session.started`.
- `source`: `processforge.runtime.<adapter>`.
- `subject`: `task_id`, `run_id`, command id, or event id.
- `project`: existing `project_id(project_root)` and `flow_label(project_root)`.
- `assignment`: only set when `task_id` is known.
- `actor`: `{ "type": "agent", "id": <agent>, "role": <role> }`.
- `data`: sanitized adapter payload.
- `correlation_id`: adapter session id, run id, or generated correlation id.

Idempotency:

- If an adapter gives a stable event id, convert it to the PF `evt_...` pattern.
- If not, derive `event_id` from `sha256(adapter, hook_event_name, session_id, cwd, timestamp bucket, payload hash)`.
- Keep `append_process_event` as the durable duplicate gate, because it already skips existing `event_id`.

Schema note: `schemas/process-event.schema.json` currently enumerates event types and may reject new `agent.*` events. The PoC can either use `event-envelope.schema.json` validation for runtime events or extend the enum deliberately.

## F. Agent Adapters

Adapter contract:

- read native hook payload from stdin or HTTP;
- identify agent, event name, cwd, project root, session id, tool/command facts;
- sanitize payload;
- POST normalized input to Runtime or fall back to a CLI command that appends the event directly;
- return the agent-specific allow/continue response format.

Adapter boundaries:

- No ProcessForge stage decisions in adapters.
- No project context resolution in adapters.
- No direct writes to `.pf/artifacts/`, except optional local debug logs under `.pf/runtime/`.

Confirmed external hook surfaces:

- Claude Code documents lifecycle hooks including session, prompt, tool-use, and stop events; handlers can be shell commands or HTTP endpoints.
- Gemini CLI documents hook commands with JSON stdin/stdout, environment variables such as project/session/cwd, exit code handling, and security warnings.

Unstable or unconfirmed surfaces:

- Codex CLI public repository and issues show hook work as experimental/evolving, including Windows and feature-flag notes, but a stable official hook reference was not found in this pass.
- Kimi CLI is a terminal agent, but stable lifecycle hook documentation was not confirmed; public discussion exists for configurable lifecycle hooks.

PoC adapter recommendation:

- Implement a generic stdin JSON adapter first.
- Add explicit Gemini-style and Claude-style mappings because their contracts are documented.
- Label any Codex/Kimi shim as experimental until stable local config and payload samples are verified.

## G. Unified MCP Interface

MCP should be a facade over PF Core and Runtime state, not a new resolver.

PoC tools:

- `pf.project_state`: returns project id, context freshness, selected process/run/task, and known blockers by calling `project_context_check_result` and reading run/task YAML.
- `pf.work_state`: returns current session, agent presence, active worker-runs, and recent runtime events.
- `pf.resolve`: resolves project/workplace/path/resource refs through existing PF resolver functions.
- `pf.event_append`: optional local-only tool to append a sanitized event through the same normalization path as hook adapters.

Later tools:

- `pf.knowledge`: expose indexed resource metadata and selected resource documents.
- `pf.templates`: list selected templates and render proposals through existing template registry logic.
- `pf.handoff`: expose process routes and handoff status.

The MCP server should be registered in workplace `registries/mcp.yaml` after it exists. Registration is metadata only; the server implementation remains in the ProcessForge distribution.

## H. Persistence And Projections

Durable facts:

- `.pf/runtime/events/events.ndjson`
- `.pf/runtime/hooks/outbox/`
- `.pf/runtime/hooks/results/`
- `.pf/runtime/current-session.json`
- `<workplace>/runtime/agent-ledger/sessions.ndjson`
- `<workplace>/runtime/agent-presence/<agent-id>/<session-id>.json`
- `.pf/runtime/agent-runs/...`

Runtime memory:

- auth token currently loaded;
- active HTTP server state;
- recent event dedup cache;
- projection cache;
- open MCP client state.

Projection for PoC:

- Generate `.pf/artifacts/pf-runtime-mcp-20260813/command-history.md`.
- Source only `events.ndjson`.
- Include timestamp, agent, cwd, command/tool, exit code/status, related task/run when known.
- Rebuild from scratch on `runtime serve --rebuild-projections` and after restart.

Do not store secrets or full chat contents in public projections. Keep private telemetry and raw payloads under `.pf/runtime/` only when explicitly needed.

## I. Security Model

Threats:

- malicious project-level hook config;
- local process POSTing fake events;
- path traversal through `project_root`;
- leaking tokens, prompts, command args, or chat content;
- hook loops and event floods;
- service accidentally executing payload-controlled commands;
- stale service pid/port state;
- agent-specific hook behavior changing under the Runtime.

Required controls:

- bind to `127.0.0.1` only;
- random bearer token per service start or explicit operator-managed token;
- token file under private workplace runtime state with restrictive permissions where supported;
- accept only onboarded PF projects: path must resolve to a directory containing `.pf/process-forge.yaml`;
- reject project roots outside allowed workplace/project roots unless explicitly configured;
- size limits for request body and per-field values;
- sanitize secret-like values using existing `redact_telemetry_value` logic;
- never execute commands from incoming event payloads;
- rate-limit or batch projection rebuilds;
- write all files atomically where possible;
- mark command/network hook execution as out of PoC unless separately approved.

## J. Minimal PoC Scope

Build only after report approval:

- `runtime serve --project-root . --workplace <workplace>` foreground service.
- `/status`: returns service version, pid, uptime, bound address, known project count.
- `/event`: accepts normalized JSON, verifies token, validates project root, appends PF event.
- One stdin adapter command: reads hook JSON from stdin and POSTs to `/event`.
- One documented adapter profile for Gemini or Claude; Codex/Kimi marked experimental until payload samples are verified.
- Projection writer: creates command history Markdown from runtime events.
- MCP facade with `pf.project_state`, `pf.work_state`, and `pf.resolve`.
- Tests/smokes:
  - CLI commands still work when runtime is stopped.
  - unauthorized `/event` returns 401.
  - invalid project root is rejected.
  - duplicate event id appends once.
  - runtime restart rebuilds projection from existing events.
  - `events-validate` remains passing.

Explicitly out of PoC:

- Windows Service installation.
- Network webhook sending.
- command-hook execution runner.
- automatic persistent daemon startup.
- full knowledge document search.
- agent-specific blocking decisions beyond pass-through allow/continue.

## K. PF Core Changes Needed

Minimal core changes:

- Add a small importable Runtime package rather than extending the monolithic CLI file for all serving logic.
- Add CLI subcommands for runtime lifecycle, for example `runtime serve`, `runtime status`, `runtime doctor`.
- Add adapter input schema and normalizer.
- Add event type policy for `agent.*` events: either extend `process-event.schema.json` or validate runtime stream with the more general event envelope.
- Add projection builder using existing NDJSON reader and event validation helpers.
- Add MCP server entrypoint that calls existing PF functions.
- Add tests for event append, auth rejection, projection rebuild, and CLI-without-runtime.

No core changes should:

- replace `.pf` file contracts;
- move business logic into MCP;
- require the service for existing CLI flows;
- store project truth only in memory.

## L. Risks And Open Questions

Risks:

- Monolithic `tools/processforge.py` makes import boundaries less clean; the PoC should keep wrapper code small and avoid circular imports.
- Existing `process-event.schema.json` enum may block new runtime event types unless extended.
- `project-context-check` is currently broken in this workspace because required capabilities are missing and project classification changed; runtime design must treat broken context as a surfaced blocker, not silently continue.
- Codex and Kimi hook APIs were not confirmed as stable official contracts during this pass.
- Loopback HTTP token security is sufficient for a local PoC, but not as strong as OS-bound IPC.
- Projection updates can race with concurrent CLI appends unless file reads tolerate partial writes and rebuilds are atomic.
- Project-level hooks can be untrusted; adapters must be opt-in and visible to the operator.

Open questions before implementation:

- Should the first concrete adapter target Gemini/Claude documented hooks, or should the PoC prioritize a Codex-labelled generic shim for local dogfooding?
- Should `agent.*` events become part of the public process event taxonomy, or remain Runtime-private envelope events for the first PoC?
- Should MCP run as a separate stdio server process or as an endpoint exposed by the same HTTP runtime process?
- Where should the long-term generated projection live: public `.pf/artifacts/projections/` or private `.pf/runtime/projections/` plus explicit export?

## External Sources Checked

- Claude Code hooks documentation: https://docs.anthropic.com/en/docs/claude-code/hooks
- Gemini CLI hooks guide: https://github.com/google-gemini/gemini-cli/blob/main/docs/cli/hooks/writing-hooks.md
- Gemini CLI hooks reference: https://github.com/google-gemini/gemini-cli/blob/main/docs/cli/hooks/reference.md
- Gemini CLI hooks index/security notes: https://github.com/google-gemini/gemini-cli/blob/main/docs/cli/hooks/index.md
- OpenAI Codex repository: https://github.com/openai/codex
- OpenAI Codex hook-related GitHub issues/discussions were used only as evidence that the public hook surface is evolving, not as a stable API contract.
- Kimi CLI repository/discussion pages were used only to check whether stable lifecycle hook documentation was discoverable; none was confirmed in this pass.

## Final Recommendation

Approve a narrow PoC only if its implementation remains interface-only: agent hooks and MCP call into PF Core, events persist through the existing event envelope, projections are rebuildable, and CLI workflows remain independent of the service. The highest-value first slice is event ingestion plus a command-history projection; MCP should expose read-only state first, then write actions after the security model has proof.
