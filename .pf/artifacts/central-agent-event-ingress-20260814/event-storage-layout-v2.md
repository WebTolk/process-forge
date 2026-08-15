# event-storage-layout-v2

Extracted verbatim in substance from the accepted architecture candidate `central-event-ingress-design-v2.md` so the storage contract has a durable standalone artifact.

## 1. Решение

Полный native поток хранится на workplace-level, а project journal остаётся фильтрованной производной.

```text
<workplace>/runtime/agent-events/
  raw/
  normalized/
  checkpoints/
  indexes/
  blobs/
  errors/
```

В public/project artifacts нельзя сохранять абсолютный путь workplace. В документах использовать только contract path shape.

## 2. Raw journal

Рекомендуемый file-first layout:

```text
runtime/agent-events/raw/
  v1/
    yyyy/
      mm/
        dd/
          hh.ndjson
```

Каждая строка raw shard:

```json
{
  "schema_version": 1,
  "raw_event_id": "raw_<hash>",
  "provider": "codex",
  "adapter": "codex-hooks",
  "native_event_type": "PostToolUse",
  "native_event_id": "...",
  "received_at": "...",
  "source_session_id": "...",
  "source_project_ref": "...",
  "correlation": {},
  "payload_version": "provider-documented-or-adapter-version",
  "raw_payload": {},
  "payload_ref": null,
  "privacy": "private"
}
```

Large payload policy:

```text
raw_payload.inline <= configured limit
raw_payload larger → blobs/<raw_event_id>.json
journal line keeps payload_ref + hash + byte_size
```

## 3. Normalized workplace journal

Normalized workplace stream is optional in first slice, but the layout is reserved:

```text
runtime/agent-events/normalized/
  v1/
    yyyy/mm/dd/hh.ndjson
```

It contains PF-normalized facts derived from raw, not provider raw payload.

## 4. Project journal

Existing project-local event journal remains:

```text
.pf/runtime/events/events.ndjson
```

It receives only selected normalized events relevant to that project. It must not receive full raw payload automatically.

## 5. Chat transcript

Existing transcript layout remains project-local:

```text
.pf/runtime/chat/transcripts/<session-id>.ndjson
```

The event journal stores metadata and `content_ref`; transcript stores content. Raw workplace journal may contain provider-native content if provider supplied it, but that does not replace ChatService.

## 6. Indexes

Indexes are derived and rebuildable:

```text
runtime/agent-events/indexes/
  raw_event_id/
  session/
  project/
  provider/
  native_event_type/
  normalized_event_type/
  time/
```

Index records should point to shard + line/offset + hash. Do not load full indexes at Runtime startup.

## 7. Checkpoints and replay

```text
runtime/agent-events/checkpoints/
  normalizers/<normalizer-id>.json
  routers/<router-id>.json
  chat/<chat-router-id>.json
  project-events/<project-id>.json
```

Checkpoint records include:

```text
last_raw_event_id
last_shard
last_offset_or_line
normalizer_version
completed_at
```

Replay must be able to run by session, project, provider, time range, or raw_event_id range.

## 8. Concurrency

Required invariant:

```text
one raw event = one complete NDJSON line or no line
```

Implementation must use an interprocess lock per shard or an equivalent atomic append strategy. Temp-file + atomic rename is required for indexes/checkpoints. The existing in-process lock is not enough for multiple agents/processes.

## 9. Retention

Default: no silent deletion.

Retention must be explicit and independently configurable for raw, normalized, chat transcripts, project events, blobs, indexes, and errors. Deletion/compaction must never break replay without an explicit operator decision.
