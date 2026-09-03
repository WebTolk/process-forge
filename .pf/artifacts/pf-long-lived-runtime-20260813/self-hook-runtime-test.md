# Self Hook Runtime Test

- date: 2026-08-13
- runtime_workplace: `D:\.agents\processforge-workplace`
- purpose: verify whether this active Codex session emits lifecycle hook events into the long-lived PF Runtime while editing `.pf` artifacts.

## Action

This artifact was created by the active Codex session after `pf runtime start`.

## Expected If Hooks Are Wired

At least one Codex hook event such as `PreToolUse`, `PostToolUse`, or file-change-related normalized event should appear in the project event journal through PF Runtime.

## Observed

- `pf runtime start --workplace D:\.agents\processforge-workplace --json` started runtime at `http://127.0.0.1:60017`, pid `19948`.
- Baseline project event count before this artifact write: `39`.
- After creating this artifact through the active Codex session, project event count remained `39`.
- Runtime operator log contained only `runtime.started`, `GET /readyz`, and later explicit status/event HTTP requests.
- Global Codex config `C:\Users\musst\.codex\config.toml` has `notify = ... turn-ended`, but no lifecycle hook section for `SessionStart`, `PreToolUse`, `PostToolUse`, `PermissionRequest`, or `SessionEnd`.

Conclusion: this active Codex session did not emit its own lifecycle hooks into PF Runtime, because no hook adapter is currently connected to the session.

## Control

A manual normalized adapter event posted to `/event` succeeded with HTTP `200` and was appended to `.pf/runtime/events/events.ndjson` at line `40`:

- `source.adapter`: `codex-hooks-manual-selftest`
- `event_type`: `agent.tool.completed`
- `payload.hook_event_name`: `PostToolUse`

Conclusion: PF Runtime ingress works; the missing piece is actual Codex hook adapter installation/loading for the Codex process.
