# Codex session read layer

ProcessForge exposes three read-only MCP tools for the active Codex session:

- `pf.session_context` returns a bounded projection of project, work, blockers,
  active agents, context freshness, resource readiness, execution readiness and
  normalized session activity.
- `pf.session_chat` returns the private, redacted PF transcript for that same
  session. It accepts `limit` (1--100), `before`/`cursor`, and an optional
  `roles` array.
- `pf.session_activity` returns bounded normalized project-event facts for that
  session. It never returns raw provider journal entries.

Each call requires an existing Agent Ledger session. `session_id` is accepted
as a tool argument (or the explicitly configured `PF_MCP_SESSION_ID`); the
optional `project_root` is only a consistency assertion. A mismatch fails
closed with `session_project_mismatch`. Stable tool error objects contain only
an error code, such as `missing_session`, `unknown_session`, `session_mismatch`,
`session_not_routed`, or `invalid_cursor`.

Read-only session tools keep context validity separate from execution blockers.
When a project snapshot is fresh but the current work lacks a capability,
`pf.session_context` still returns the session projection and reports the
capability under `execution_readiness.missing_capabilities`. `pf.search` and
`pf.resolve` may still read authorized fresh resources; actions that actually
need the missing capability remain blocked.

## Conversation capture

`tools/pf_runtime/codex_hooks.py` stores every registered Codex hook payload
raw-first through the existing ingress path. `UserPromptSubmit` captures the
user message; `Stop` captures `last_assistant_message`; and `SubagentStop`
captures the subagent final message. All three use the pre-existing transcript
writer, deterministic message identity and replay rules. Project events retain
only message metadata, never transcript content.

The `Stop` and `SubagentStop` handlers output `{}`: this is valid neutral
Codex hook protocol and does not block, rewrite or continue a turn. On a
delivered `SessionStart`, the observer supplies the Ledger session id as
additional context so that the current turn can invoke session MCP methods
without manually locating PF files. A session id is project-scoped context,
not a cross-project capability.

## Opt-in hook registration

The distribution does not alter a user's Codex files automatically. To inspect
or install project-local observation hooks, run:

```powershell
python tools/pf_runtime/codex_integration.py status --project-root .
python tools/pf_runtime/codex_integration.py install --project-root . --apply
python tools/pf_runtime/codex_integration.py remove --project-root . --apply
```

The installer manages only `<project>/.codex/hooks.json`, merges with existing
handlers, is idempotent, writes a timestamped backup before a change, and
removes only its own handlers. `install` without `--apply` is dry-run. Codex
still requires the project hook layer to be trusted; inspect real registration
with `/hooks` after restarting or reloading Codex.

## MCP host configuration

PF registry metadata and Codex MCP host configuration are deliberately
separate. ProcessForge can manage the Codex stdio MCP registration explicitly:

```powershell
python bin/pf.py codex-mcp status --workplace <processforge-workplace>
python bin/pf.py codex-mcp install --workplace <processforge-workplace> --apply
python bin/pf.py codex-mcp remove --workplace <processforge-workplace> --apply
```

The equivalent manual registration uses an explicit installed-distribution path
and workplace, for example:

```powershell
codex mcp add processforge -- py -3 "<processforge-install>/tools/pf_runtime/mcp_server.py" --workplace "<processforge-workplace>"
```

Do not put a mutable current-session id into a shared host configuration. When
a session is explicitly configured on a server process, every different tool
argument is rejected as `session_mismatch`; a call cannot switch that process
to another Ledger session. The
host may start the stdio process with environment variables, but its static MCP
configuration has no documented per-turn session interpolation. The registered
`SessionStart` hook therefore provides the current Ledger id to the turn, and
the MCP call supplies it explicitly. This preserves the one Ledger binding and
avoids a second session-to-project table.

MCP setup is opt-in and must be verified separately from hook registration:
run `codex mcp list` (and `/mcp` in an active client) for the server, and
`/hooks` for trusted matching hook handlers.

The stdio MCP process is host-owned. It is not a Windows autostart target and is
not a detached Runtime service. Restart or reload Codex after changing the host
registration so a fresh session starts a connected MCP process.
