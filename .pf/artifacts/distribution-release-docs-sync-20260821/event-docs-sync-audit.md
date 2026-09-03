# Event documentation synchronization audit

Status: documentation update required.

## Materially outdated pages

`docs/concepts/hooks-events.md` and its Russian mirror describe only project-local events and a three-hook Codex adapter. They omit the workplace-level raw journal and `UserPromptSubmit` conversation capture.

`process-events.md`, `processforge-events.md`, `runtime-model.md`, `chat-relay.md`, and both known-limitations pages describe the older project-runtime model without explaining the raw-first ingress boundary.

## Verified model to document

```text
native agent hook/event
  -> provider adapter
  -> workplace private raw ingress
  -> normalization and project-scope validation
  -> project event, conversation record, telemetry, Ledger, or no derived effect
```

Workplace storage is `runtime/agent-events/`: raw hourly shards, `raw_event_id` and optional native-identity indexes, quarantine/error records, and replay checkpoints. Raw records are private.

Project-side records remain under `.pf/runtime/`, including project event journals and private chat transcripts. `chat.message.recorded` is metadata-only by default; full content is not copied into the event/outbox.

`session_replay.py` replays accepted Codex raw records for one declared session and project. It restores missing normalized derived events, deduplicates by existing event id, writes a checkpoint, rejects scope mismatches, and reports unsupported mappings. It does not rebuild generic conversation content.

The update must state that generic Codex assistant/subagent response capture is not currently demonstrated. English and Russian pages must use the same capability, privacy, and limitation claims; public documentation must not link to `.pf/artifacts` or local machine paths.
