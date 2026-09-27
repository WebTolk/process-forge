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
.pf/runtime/events/events.ndjson
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

## Project event journal writers

Project event-id deduplication and append use the same cross-process writer
lock. A complete UTF-8 record is appended and flushed before success; hooks
dispatch after releasing the lock. A lock failure is reported explicitly.
Already running clients keep their loaded code until their normal restart or
reconnect, so the guarantee applies to writers using the updated Core.

Malformed historical records must retain their original evidence. Do not
replace or truncate a live journal to remove a bad line: concurrent appended
events and byte offsets would be at risk. A reviewed operator recovery may
quarantine an exact invalid fragment, preserve its newline and byte length,
and verify every valid byte plus later appends. Blank lines are ignored by the
existing NDJSON readers. Keep the original backup and a separate repair audit;
do not reconstruct an event id or payload from an incomplete timestamp.
