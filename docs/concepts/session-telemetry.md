# Session Telemetry

Optional operational detail uses the separate [diagnostics contract](diagnostics.md).
Its severity/profile/sink settings never disable the required session or process
facts described here.

Every ProcessForge agent session writes private telemetry so later reviews can
explain how context was selected and why the agent stopped.

Default paths for new projects:

```text
.pf/runtime/sessions/<session-id>.yaml
.pf/runtime/telemetry/<session-id>.ndjson
.pf/runtime/events/events.sqlite3
.pf/runtime/hooks/
.pf/runtime/chat/
```

`.pf/runtime/` is private and ignored by default. Public reports may summarize
results, but they must not copy private telemetry, hook outbox, or chat payloads.

## Minimum Events

Session telemetry uses NDJSON. The required event vocabulary is:

- `session_start`
- `session_end`
- `snapshot_check`
- `source_read`
- `assignment_loaded`
- `capability_check`
- `tool_selected`
- `tool_invoked`
- `tool_failed`
- `mcp_check`
- `fallback_used`
- `conflict_detected`
- `file_scope_checked`
- `artifact_written`
- `review_requested`
- `handoff_created`
- `doctor_run`

Events must avoid secrets, tokens, passwords, and large source-code excerpts.
Private telemetry may include diagnostic paths when needed, but public summaries
must stay sanitized.

Telemetry describes what the agent did inside one session. Process events
describe flow-level facts that hooks or future consumers can observe. Chat relay
records conversation messages separately under `.pf/runtime/chat/transcripts/`
and emits `chat.message.recorded` with metadata-only content by default.

## Project journals are separate

Project events now use transactional SQLite in
`.pf/runtime/events/events.sqlite3`. Unique SQL admissions and pending dispatch
replace the old NDJSON append/lock model for that journal. Raw hook input has
its own `.pf/runtime/agent-events/hooks.sqlite3`. Session telemetry remains
NDJSON, as do workplace events, Agent Ledger history and private transcripts.
See [journal ownership and migration](hook-journal-sqlite.md).

Do not apply line or byte-offset repairs to a SQLite database. Preserve the
original evidence and use a reviewed operator backup/recovery procedure for
the affected owner. Frozen legacy NDJSON sources remain migration inputs;
they are not the active project event journal.
