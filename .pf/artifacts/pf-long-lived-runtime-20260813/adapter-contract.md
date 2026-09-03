# PF Runtime Adapter Contract

## Purpose

PF Runtime is adapter-neutral. Codex hooks are the first adapter source, but the runtime boundary is a normalized local event API that can also be fed by Claude, Gemini, local shell agents, IDE agents, or future MCP/app-server bridges.

## Runtime Boundary

Adapters must send normalized JSON events to:

- preferred online path: `pf runtime event --workplace <workplace> --input <event.json>`
- fallback direct path: `pf runtime-host event --workplace <workplace> --input <event.json>`

The online path requires the long-lived runtime process and uses authenticated loopback IPC internally. The fallback path writes through existing PF Core logic without requiring the long-lived process.

Adapters must not call arbitrary shell execution through runtime IPC. They may only submit facts, register sessions, and read scoped state through the runtime commands.

## Normalized Event Shape

Required:

- `schema_version: 1`
- `event_type`: ProcessForge normalized event name such as `agent.session.started`, `agent.command.completed`, or `agent.tool.failed`

Routing:

- `project_root` or `cwd` identifies the ProcessForge project.
- `session_id` identifies the agent/runtime session.
- `agent_id` identifies the concrete agent instance when available.
- `source.adapter` names the adapter, for example `codex-hooks`, `codex-app-server`, `claude-hooks`, `gemini-cli`, or `local-shell-agent`.

Payload:

- `payload` may keep adapter-native details such as Codex `hook_event_name`, `turn_id`, `tool_name`, `tool_use_id`, `permission_mode`, model slug, or summarized tool result.
- Adapter-native transcript files are diagnostic references only. They are not the durable event API.

## Codex Adapter Mapping

Use `.pf/artifacts/pf-runtime-director-ledger-20260813/codex-events-reference.md` as the Codex source reference.

Initial Codex hook mapping:

- `SessionStart` -> `agent.session.started`, `agent.session.resumed`, or `agent.session.compacted`
- `UserPromptSubmit` -> `agent.prompt.submitted`
- `PreToolUse` -> `agent.command.started`, `agent.file.change_planned`, or `agent.tool.started`
- `PermissionRequest` -> `agent.permission.requested` and optional `agent.permission.decided`
- `PostToolUse` -> `agent.command.completed`, `agent.command.failed`, `agent.file.changed`, `agent.tool.completed`, or `agent.tool.failed`
- `PreCompact` / `PostCompact` -> `agent.session.compaction_started` / `agent.session.compacted`
- `SubagentStart` / `SubagentStop` -> `agent.subagent.started` / `agent.subagent.completed`
- `Stop` -> `agent.turn.completed`
- `SessionEnd` -> `agent.session.ended`

## Multi-Agent Rules

- Runtime identity is `workplace` scoped, not project scoped.
- Session registration binds one `session_id` to one project handle.
- Read endpoints must enforce that a session cannot read another project by passing a conflicting `project_root`.
- Multiple adapters can submit events for different sessions in the same workplace.
- Agent-specific logic belongs in adapter mapping, not in PF Core or the runtime service.

## Adapter Implementation Checklist

- Resolve `cwd` to a ProcessForge project before submitting if possible.
- Preserve native event ids when stable; otherwise let runtime derive a stable event id.
- Always include `source.adapter`.
- Prefer compact payloads; large transcripts should be referenced, not copied.
- On runtime unavailable, use `runtime-host event` or a durable adapter-local outbox for replay.
- Treat auth token files under `workplace/runtime/pf-runtime/token.json` as local secrets.
