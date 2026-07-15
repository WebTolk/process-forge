# Session Telemetry

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
