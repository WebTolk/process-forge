# Codex Lifecycle Events Reference For PF Runtime

- date: 2026-08-13
- scope: reference material for ProcessForge Runtime host integration with Codex
- sources: official OpenAI documentation only

The ready-to-copy hook configuration example is kept beside this reference as
[`codex-hooks.json`](codex-hooks.json). It is intentionally not placed in
`.codex/hooks.json`, so it remains reference material and does not enable hooks
implicitly for every local Codex session.

## Runtime Integration Decision

PF Runtime should catch facts from the Codex process, but it should not treat the session transcript as the primary API. Official OpenAI documentation describes two usable integration channels:

- Codex lifecycle hooks for practical local event capture.
- Codex app-server JSON-RPC notifications for deeper rich-client integrations.

For the next ProcessForge slice, use hooks first. Treat app-server as the later richer transport when PF Runtime needs full `thread/*`, `turn/*`, and `item/*` streams.

## Stable Hook Channel

Codex hooks are lifecycle handlers loaded from `hooks.json` or inline `[hooks]` tables in config. Useful locations include user-level `~/.codex/hooks.json`, user-level `~/.codex/config.toml`, project-level `<repo>/.codex/hooks.json`, and project-level `<repo>/.codex/config.toml`. Project-local hooks require the project `.codex/` layer to be trusted.

Every command hook receives one JSON object on stdin. Common input fields:

- `session_id`: current Codex session id; subagent hooks use the parent session id.
- `transcript_path`: session transcript path when available.
- `cwd`: working directory for the session.
- `hook_event_name`: current hook event name.
- `model`: active model slug.
- `permission_mode`: present for several lifecycle events, including `SessionStart`, tool hooks, prompt hooks, subagent hooks, and `Stop`.

Important constraint: `transcript_path` is a convenience path, not a stable hook interface. PF Runtime may inspect it for diagnostics, but should not use it as the durable event API.

## Hook Lifecycle Map

### Session Start

- Codex event: `SessionStart`
- Matcher applies to `source`.
- `source` values: `startup`, `resume`, `clear`, `compact`.
- PF event mapping:
  - `startup` -> `agent.session.started`
  - `resume` -> `agent.session.resumed`
  - `compact` -> `agent.session.compacted` plus session continuation context if needed

### User Prompt

- Codex event: `UserPromptSubmit`
- Use for model-facing user prompt submission.
- PF event mapping: `agent.prompt.submitted`.

### Tool Use Before Execution

- Codex event: `PreToolUse`
- Fields include `turn_id`, `tool_name`, `tool_use_id`, and `tool_input`.
- Supported paths include shell as `Bash`, `apply_patch`, MCP tools, and local function tools. Some specialized tools may opt out.
- PF event mapping:
  - `Bash` command intent -> `agent.command.started`
  - `apply_patch` or file-write intent -> `agent.file.change_planned`
  - MCP/local tool intent -> `agent.tool.started`

### Permission Request

- Codex event: `PermissionRequest`
- Fields include `turn_id`, `tool_name`, and `tool_input`.
- Hooks may allow or deny. If multiple hooks decide, deny wins.
- PF event mapping:
  - request observed -> `agent.permission.requested`
  - allow/deny hook decision -> `agent.permission.decided`

### Tool Use After Execution

- Codex event: `PostToolUse`
- Runs after supported tools produce output, including non-zero Bash exits.
- Fields include `turn_id`, `tool_name`, `tool_use_id`, `tool_input`, and `tool_response`.
- It cannot undo side effects from a tool that already ran.
- PF event mapping:
  - shell result -> `agent.command.completed` or `agent.command.failed`
  - file edit result -> `agent.file.changed`
  - MCP/local tool result -> `agent.tool.completed` or `agent.tool.failed`

### Compaction

- Codex events: `PreCompact`, `PostCompact`.
- Manual and automatic compaction should be treated as session-maintenance facts.
- PF event mapping:
  - `PreCompact` -> `agent.session.compacting`
  - `PostCompact` -> `agent.session.compacted`

### Subagents

- Codex events: `SubagentStart`, `SubagentStop`.
- Fields include subagent identity/type and transcript information.
- PF event mapping:
  - `SubagentStart` -> `agent.subagent.started`
  - `SubagentStop` -> `agent.subagent.completed`

### Turn Stop

- Codex event: `Stop`.
- Fields include `turn_id`, `stop_hook_active`, and the last assistant message.
- PF event mapping: `agent.turn.completed`.

### Session End

- Codex event: `SessionEnd`.
- Always runs synchronously.
- It runs for the main thread when a conversation is archived or deleted while open, when Codex closes normally, or after a conversation has been idle and closed in all connected clients for 30 minutes.
- It does not run for subagents.
- `reason` currently uses `other`.
- PF event mapping: `agent.session.ended`.

## Background Hooks

Hooks normally block until the command exits. A command hook can set `async = true` to run in the background.

Operational constraints:

- Codex runs up to eight background hooks concurrently per session.
- Background hook completion order may differ from start order.
- Background hooks cannot block, approve, rewrite, or control the operation that triggered them.
- When the session ends, unfinished background hooks are canceled and undelivered output is discarded.
- `SessionEnd` hooks always run synchronously.

PF Runtime should use synchronous hooks for lifecycle facts that must be durable, especially session start/end and permission decisions. Background hooks are acceptable for derived projections or low-priority telemetry.

## App-Server Event Channel

Codex app-server is the deeper integration API used by rich clients. It provides JSON-RPC methods and notifications over stdio, WebSocket, or Unix socket transports.

Relevant lifecycle:

- `thread/start`, `thread/resume`, `thread/fork` create or continue a thread.
- `thread/started` is emitted after thread start/fork.
- `thread/status/changed` reports loaded thread runtime status changes.
- `thread/closed`, `thread/archived`, `thread/deleted`, and `thread/unarchived` report thread lifecycle changes.
- `turn/*` notifications describe turn progress.
- `item/*` notifications describe item progress inside a turn.
- Manual compaction emits standard `turn/*` and `item/*` notifications, including context-compaction item lifecycle.

App-server can stream richer items such as command execution, file changes, MCP tool calls, dynamic tool calls, web search, reasoning, and agent messages. This is the better future source for full ProcessForge projections, but it is heavier than hooks and some transports are documented as experimental or unsupported for production workloads.

## PF Runtime Event Taxonomy Recommendation

Minimum normalized event names for Codex adapter input:

- `agent.session.started`
- `agent.session.resumed`
- `agent.session.ended`
- `agent.prompt.submitted`
- `agent.turn.started`
- `agent.turn.completed`
- `agent.command.started`
- `agent.command.completed`
- `agent.command.failed`
- `agent.tool.started`
- `agent.tool.completed`
- `agent.tool.failed`
- `agent.file.change_planned`
- `agent.file.changed`
- `agent.permission.requested`
- `agent.permission.decided`
- `agent.session.compacting`
- `agent.session.compacted`
- `agent.subagent.started`
- `agent.subagent.completed`

Minimum routing keys:

- `session_id`
- `turn_id`
- `cwd`
- `project_root` after PF Project Router resolution
- `agent_id`
- `tool_name`
- `tool_use_id`
- `event_id` or deterministic hash

## Security And Reliability Notes

- Do not execute commands from hook payloads.
- Do not store raw prompts, full transcripts, or secrets in public `.pf/artifacts`.
- Redact hook payloads before appending ProcessForge events.
- Treat `cwd` as a routing hint, not as project identity.
- Verify `.pf/process-forge.yaml` before accepting a project route.
- Use idempotent event ids, because hooks or app-server clients can retry.
- Prefer synchronous hooks for ledger-critical events.

## Official Sources

- OpenAI Docs, Hooks: https://learn.chatgpt.com/docs/hooks
- OpenAI Docs, Advanced Configuration hooks: https://learn.chatgpt.com/docs/config-file/config-advanced
- OpenAI Docs, Configuration Reference: https://learn.chatgpt.com/docs/config-file/config-reference
- OpenAI Docs, Codex App Server: https://learn.chatgpt.com/docs/app-server
