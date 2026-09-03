# central-event-ingress-design-v2

Дата: `2026-08-14`
Задача: `central-ingress-architecture-corrected-20260814`
Режим: planning-only, без изменений кода.

## 1. Исправленный архитектурный вывод

Текущий runtime-путь уже имеет полезный единый вход, но он не является raw-first:

```text
codex_hooks.py
→ normalized_event(...)
→ Runtime /event или host.ingest_event fallback
→ host.normalize_event(...)
→ ledger_from_event(...)
→ append_process_event(...)
→ rebuild projections
```

Это сохраняет текущие normalized `SessionStart` / `SessionEnd` / `PostToolUse` semantics, но противоречит целевому инварианту из master prompt: сначала durable raw факт, затем интерпретация.

Исправленная архитектура должна быть такой:

```text
provider hook payload
→ thin provider adapter
→ Central Event Ingress Core
→ durable workplace raw append
→ receipt
→ normalization / enrichment
→ route decisions
→ Ledger / ChatService / project events / projections
```

Главное решение: `Runtime /event` и direct fallback остаются transport-адаптерами, но оба делегируют в один Core ingress. Provider adapters не пишут напрямую в Ledger, project journal или chat transcript.

## 2. Canonical Core boundary

Provider-neutral Core API должен принимать не Codex-specific `SessionStart` / `PostToolUse`, а native envelope:

```text
NativeAgentEvent
- schema_version
- provider
- adapter
- native_event_type
- native_event_id
- received_at
- source_session_id
- source_project_ref
- correlation
- payload_version
- raw_payload
- provenance
```

Концептуальный API:

```text
receipt = ingress.accept(native_event)
```

Receipt:

```text
raw_event_id
accepted
deduplicated
raw_location
normalized_event_ids
chat_message_ids
routing_status
diagnostics
```

`accepted=true` означает durable raw acceptance. Adapter не обязан ждать завершения всех derived sinks.

## 3. Provider adapters

Adapter обязан делать только минимальную работу:

- принять официальный hook/event payload provider-а;
- проверить, что payload является JSON object и не превышает лимит;
- заполнить provider-neutral raw envelope;
- передать envelope в central ingress;
- вернуть успех после durable raw receipt.

Adapter не должен:

- выбирать project journal напрямую;
- писать Ledger напрямую;
- выбрасывать unknown native events;
- строить Core вокруг provider vocabulary;
- считать `transcript_path` canonical API.

Для Codex первый slice должен расширить raw capture до всех официально подтверждённых native events, но normalized mapping делать только там, где семантика доказана.

## 4. Нормализация

Normalized PF event остаётся в формате `event-envelope.schema.json`.

Текущие semantics нужно сохранить:

- `SessionStart/startup` → `agent.session.started`;
- `SessionStart/resume` → `agent.session.resumed`;
- `SessionStart/compact` → текущая `agent.session.compacted` semantics сохраняется, но Ledger check-in не изобретается без явного решения;
- `SessionEnd` → `agent.session.ended`;
- `PostToolUse` → `agent.command.completed`;
- `PostToolUse` с `tool_name != Bash` → `agent.tool.completed`.

Unknown native event:

```text
raw capture = yes
normalized PF event = no или diagnostic generic wrapper
project routing = no, пока нет политики
```

Normalization failure после raw append не считается потерей события: raw уже должен быть replayable.

## 5. Chat boundary

Существующая chat-модель сохраняется:

```text
.pf/runtime/chat/transcripts/<session-id>.ndjson
```

Строка transcript соответствует `chat-message.schema.json`. `chat.message.recorded` остаётся metadata event с `content_ref`, `content_hash`, `redaction`, и без полного content по умолчанию.

Automatic chat capture должен использовать тот же внутренний ChatService, что и ручной `chat-record`:

```text
native provider message event
→ raw append
→ normalize chat candidate
→ ChatService.append_message(...)
→ chat.message.recorded
```

Нельзя создавать параллельную сущность `ChatLog`. Tool stdout не является assistant message без явной provider semantics.

## 6. Ledger ownership

Agent Ledger остаётся canonical source of truth для `session -> project`.

Central ingress может инициировать существующие Core-команды Ledger только после raw append и только из normalized lifecycle events:

- start/resume → check-in;
- meaningful activity → heartbeat;
- end/stop → checkout.

Если session известна и привязана к другому project, событие остаётся raw, но project routing блокируется как unauthorized/mismatch.

## 7. Runtime fallback

Сейчас fallback вызывает `host.ingest_event(...)`, то есть проходит тем же normalized-first путём. В исправленной архитектуре fallback должен вызывать тот же Core ingress, что и Runtime `/event`.

```text
Runtime available:
adapter → Runtime /event → Core ingress

Runtime unavailable:
adapter → local Core ingress fallback
```

Разница transport-а не должна менять idempotency, raw storage, routing или Ledger semantics.

## 8. Ошибки

Минимальные классы:

- `invalid_envelope`: raw envelope невалиден до durable write;
- `unauthorized`: transport/auth отказ;
- `oversized_payload`: payload превышает лимит;
- `raw_persistence_failure`: hard error, receipt не выдаётся;
- `normalization_failure`: raw сохранён, derived processing deferred/failed;
- `routing_deferred`: project/session пока не разрешены;
- `routing_failure`: route запрещён или невозможен;
- `unknown_provider_event`: raw сохранён, normalized mapping отсутствует;
- `session_unresolved`;
- `project_unresolved`;
- `project_session_mismatch`.

## 9. Minimal implementation sequence

1. Characterization текущего поведения `SessionStart`, `SessionEnd`, `PostToolUse`, Runtime `/event`, fallback, Ledger, project journal, dedupe.
2. Добавить Core-level raw envelope и file-first raw journal writer.
3. Добавить central ingress service в Core: raw append, receipt, normalization dispatch, route dispatch.
4. Переключить Runtime `/event` на Core ingress.
5. Переключить direct fallback на тот же Core ingress.
6. Переключить Codex adapter с pre-normalized event на raw native envelope.
7. Сохранить текущую normalized semantics для уже поддержанных Codex событий.
8. Добавить raw capture для всех подтверждённых Codex native events.
9. Подключить automatic chat capture только для provider events, где content реально есть.
10. Добавить replay smoke на одну session.

## 10. Открытые риски

- File locking должен быть межпроцессным; текущий `RLock` достаточен только внутри одного процесса.
- Raw/chat payload содержит секреты, поэтому нельзя писать его в operator log, public artifacts или release archive.
- Provider contracts могут измениться; adapter capabilities должны быть версионированы.
- `process-event.schema.json` и `processforge-event.schema.json` не должны стать второй canonical event schema.
- Полный parsing `transcript_path` опасен без стабильного официального формата.

---

# event-storage-layout-v2

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

Retention must be explicit and independently configurable for:

- raw;
- normalized;
- chat transcripts;
- project events;
- blobs;
- indexes;
- errors.

Deletion/compaction must never break replay without an explicit operator decision.

---

# event-routing-policy-v2

## 1. Routing stages

Routing starts only after durable raw append.

```text
accepted raw
→ resolve session/project
→ normalize where meaningful
→ route to sinks
→ checkpoint
```

If routing fails, raw remains durable and replayable.

## 2. Project resolution

Resolution order:

1. Ledger session binding, if `source_session_id` is known.
2. Bootstrap lifecycle event with trusted `cwd`/`project_root` for `agent.session.started` or `agent.session.resumed`.
3. Explicit project ref from raw envelope, only after validation through Core project resolution.
4. Deferred if session/project cannot be safely resolved.

Never route an event into an arbitrary project because `cwd` exists in raw payload.

## 3. Mismatch policy

If Ledger says `session_id -> project A` and event requests project B:

```text
raw accepted = yes
project route = rejected
ledger write = no
chat write = no
diagnostic = project_session_mismatch
```

This preserves forensic data without cross-project contamination.

## 4. Sink policy

| Sink | Receives | Rule |
|---|---|---|
| Workplace raw journal | every accepted native event | mandatory |
| Workplace normalized journal | normalized facts | optional first slice, required later |
| Agent Ledger | lifecycle/activity facts only | after normalization and route validation |
| Chat transcript | provider message content only | through ChatService |
| Project events.ndjson | selected project-relevant normalized events | never raw dump |
| Projections/work-state | derived events | rebuildable, not ingress owners |
| Hooks outbox/results | outbound delivery only | not inbound raw storage |

## 5. Current semantics preservation

The first implementation slice must preserve the current observable behavior for supported Codex events:

```text
SessionStart startup/resume → Ledger check-in + project event
SessionEnd → Ledger checkout + project event
PostToolUse Bash → agent.command.completed + heartbeat when presence exists
PostToolUse non-Bash → agent.tool.completed + heartbeat when presence exists
```

Dedupe must prevent duplicate project events, Ledger activity, and chat messages on repeated delivery.

## 6. Unknown and raw-only events

Unknown provider events:

```text
raw journal = append/dedupe
normalized event = none unless generic diagnostic is explicitly enabled
project journal = none
replay status = pending/unsupported_mapping
```

This is required for future provider fields and new hook types.

## 7. Offline and replay

Runtime unavailable must not lose hook events. Direct fallback writes to the same raw journal and uses the same idempotency keys.

Replay rules:

- do not rewrite the same raw record;
- re-run normalization by version;
- route only missing derived records;
- use deterministic normalized ids derived from `raw_event_id + normalizer_version + semantic target`;
- support replay after Ledger resolution for previously deferred events.

## 8. Privacy and release boundary

Raw/chat streams are private runtime data:

- not tracked by git;
- not copied to release archives;
- not written into public artifacts;
- not sent to outbound hooks unless an explicit export path requests sanitized/full content;
- not logged in operator diagnostics.

`transcript_path` is provenance/recovery metadata only. It must be validated and must not be parsed as canonical input unless provider contract makes that format stable.

## 9. Acceptance tests for the future implementation

Required focused tests:

- every confirmed Codex native event raw-captured;
- unknown native event raw-captured;
- malformed envelope rejected before receipt;
- oversized payload rejected safely;
- concurrent writers preserve NDJSON line integrity;
- duplicate delivery does not duplicate normalized/project/chat records;
- unresolved session raw-captured but not misrouted;
- project A event never lands in project B;
- Runtime down path and Runtime up path produce equivalent durable results;
- replay after crash after raw append completes derived routing without duplicates;
- raw/chat files remain private and absent from release/public artifacts.
