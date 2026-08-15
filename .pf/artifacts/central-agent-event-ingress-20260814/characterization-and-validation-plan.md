# characterization-and-validation-plan

Дата: `2026-08-14`
Задача: `central-ingress-characterization-plan-20260814`
Режим: planning-only, без изменений кода.

## 1. Цель

Зафиксировать план проверок для первого минимального slice Central Agent Event Ingress, чтобы будущая реализация была raw-first, но не сломала текущее наблюдаемое поведение Runtime `/event`, Codex hook adapter, Ledger lifecycle, project routing, dedupe, chat transcript и release/privacy boundaries.

План применим после архитектурного решения `central-event-ingress-design-v2`, `event-storage-layout-v2`, `event-routing-policy-v2` и `idempotency-and-replay-contract`.

## 2. Текущее поведение, которое надо характеризовать до изменений

Обязательные characterization tests перед implementation patch:

| Область | Текущий инвариант |
|---|---|
| Codex `SessionStart/startup` | нормализуется в `agent.session.started`; успешный bootstrap session делает Ledger check-in и project event |
| Codex `SessionStart/resume` | нормализуется в `agent.session.resumed`; разрешён как bootstrap event |
| Codex `SessionStart/compact` | нормализуется в `agent.session.compacted`; не надо изобретать новый Ledger check-in без отдельного решения |
| Codex `SessionEnd` | нормализуется в `agent.session.ended`; при наличии presence делает Ledger checkout |
| Codex `PostToolUse` с `tool_name == "Bash"` или пустым | нормализуется в `agent.command.completed`; при наличии presence делает heartbeat |
| Codex `PostToolUse` с `tool_name != "Bash"` | нормализуется в `agent.tool.completed`; при наличии presence делает heartbeat |
| Unsupported Codex hooks | сейчас возвращают `status=ignored`; после slice должны быть raw-captured, но не должны получать ложную PF-normalization |
| Runtime `/event` | требует bearer auth, принимает normalized event, делегирует в host ingest |
| Direct fallback | при недоступном Runtime вызывает локальный ingest; результат должен стать эквивалентным Runtime path |
| Dedupe | повторный normalized `event_id` не создаёт второй project event и не повторяет Ledger effect |
| Session/project mismatch | routed session не может писать в другой project; сейчас это отказ, в новой архитектуре raw сохраняется, derived route блокируется |
| Chat manual `chat-record` | пишет `.pf/runtime/chat/transcripts/<session>.ndjson`, создаёт `msg_<uuid>` и private `chat.message.recorded` metadata event |
| Project journal | `.pf/runtime/events/events.ndjson` содержит только project-relevant normalized events, не raw payload |
| Hooks outbox/results | outbound delivery, не inbound raw journal |

## 3. Минимальный набор тестов первого slice

### 3.1 Characterization suite перед изменениями

Создать или обновить focused tests, которые запускаются на временных project/workplace fixtures и сохраняют baseline:

1. `SessionStart/startup` через текущий Codex adapter:
   - ожидается `status=delivered`;
   - project event type `agent.session.started`;
   - Ledger presence создана;
   - повторная доставка возвращает duplicate/no-op для derived sinks.

2. `SessionStart/resume`:
   - event type `agent.session.resumed`;
   - session routed в тот же project;
   - повтор не создаёт второй project event.

3. `SessionStart/compact`:
   - event type `agent.session.compacted`;
   - нет нового непредусмотренного lifecycle effect.

4. `SessionEnd` после start:
   - event type `agent.session.ended`;
   - Ledger checkout выполнен один раз;
   - replay/retry не повторяет checkout.

5. `PostToolUse` для `Bash`:
   - event type `agent.command.completed`;
   - heartbeat выполняется при существующей presence;
   - legacy normalized id сохраняется.

6. `PostToolUse` для не-`Bash` tool:
   - event type `agent.tool.completed`;
   - heartbeat выполняется при существующей presence;
   - отдельный smoke закрывает текущий пробел покрытия.

7. Unsupported native Codex event, например `Notification` или `Stop`:
   - baseline фиксирует текущий `ignored`;
   - post-implementation expectation меняется на raw accepted + no normalized project event.

### 3.2 Raw capture tests

Для новой Core ingress реализации:

| Case | Ожидание |
|---|---|
| Every confirmed Codex native event | raw record accepted and durable before derived routing |
| Unknown future native event | raw accepted, `routing_status=pending/unsupported_mapping`, no project event by default |
| Malformed/non-object envelope | rejected before receipt, no raw id assigned |
| Missing required envelope fields | rejected as `invalid_envelope` unless policy explicitly allows fallback |
| Unknown payload fields | preserved byte-for-byte in canonical raw payload representation |
| Multiline/code block/Unicode payload | valid NDJSON line, stable hash, no truncation |
| Oversized inline payload | either safe reject or blob policy path; no partial line |
| Large payload blob | journal line contains `payload_ref`, hash and byte size; blob is private runtime data |

### 3.3 Idempotency and duplicate delivery

Required checks:

1. Same provider payload delivered twice through Runtime path:
   - same `raw_event_id`;
   - second receipt `deduplicated=true`;
   - one raw line;
   - no duplicate project event, Ledger effect or chat message.

2. Same provider payload delivered once through Runtime path and once through fallback:
   - same `raw_event_id`;
   - same derived ids;
   - same routing decision.

3. Stable provider native identity with changed payload:
   - detected by native-identity conflict index without `raw_payload_hash`;
   - conflicting payload quarantined under private runtime errors;
   - no derived routing.

4. Artificial raw id collision:
   - quarantined as `raw_event_id_hash_collision`;
   - original raw record not overwritten.

5. Crash after raw append before routing:
   - retry returns original raw location;
   - missing-only repair completes derived effects;
   - no duplicates.

### 3.4 Replay tests

Replay smoke for one session is mandatory in the first slice.

Cases:

| Scenario | Expected result |
|---|---|
| Replay by `raw_event_id` | routes only missing derived effects |
| Replay by session | reconstructs project events/Ledger/chat for that session without raw rewrite |
| Replay after unresolved session later appears in Ledger | previously deferred raw event routes only after safe resolution |
| Replay with unsupported native event | remains raw-only/pending, no invented PF event |
| Replay with changed normalizer version | deterministic versioned derived ids; existing conflicting derived content quarantined |
| Checkpoint write interruption | temp-file + atomic rename prevents corrupt checkpoint from becoming authoritative |

## 4. Routing and authorization tests

1. Project A session event delivered with project B ref:
   - raw accepted;
   - project route rejected;
   - no Ledger write;
   - no chat write;
   - diagnostic `project_session_mismatch`.

2. Unknown non-bootstrap session:
   - raw accepted;
   - route deferred or rejected according to policy;
   - no arbitrary routing by `cwd`.

3. Bootstrap `agent.session.started` with trusted project ref:
   - route allowed;
   - Ledger check-in;
   - project event created.

4. Explicit `source_project_ref`:
   - routed only after Core project resolution;
   - raw payload `cwd` alone is never sufficient for cross-project routing.

5. Project journal:
   - contains selected normalized event only;
   - never contains full raw payload automatically.

## 5. Runtime unavailable / fallback tests

| Case | Expected result |
|---|---|
| Runtime running | adapter -> Runtime `/event` -> same Core ingress |
| Runtime stopped | adapter -> local Core ingress fallback |
| Runtime timeout/error | durable fallback, hook does not fail Codex turn |
| Runtime up/down duplicate pair | one raw identity and one derived effect set |
| Concurrent fallback writers | valid NDJSON, no interleaved lines, no duplicate derived effects |

## 6. Concurrency tests

Minimum stress profile:

```text
10_000 native events
multiple sessions
multiple projects
parallel Runtime and fallback writers
mixed known and unknown event types
```

Assertions:

- one raw event is one complete NDJSON line or no line;
- shard-level interprocess locking or equivalent atomic append is proven;
- raw id index has no torn writes;
- checkpoint/index writes use temp-file + atomic rename;
- Runtime startup does not load unbounded indexes into memory;
- project routing remains isolated under parallel writes;
- replay after stress completes missing derived effects only.

## 7. Chat validation tests

1. Manual `chat-record` remains compatible:
   - `msg_<uuid>` message id;
   - transcript line validates;
   - `chat.message.recorded` metadata event remains private;
   - default event has `content_ref`/`content_hash`, not full content.

2. Automatic provider chat capture:
   - uses existing ChatService/transcript sink;
   - deterministic `chat_message_id`;
   - duplicate provider delivery does not append a second transcript line;
   - user, assistant and subagent roles are captured only when provider event supplies real content;
   - empty/absent message produces no invented content;
   - Unicode, code blocks and large text preserve content hash.

3. Tool output:
   - not treated as assistant chat unless provider semantics explicitly says it is assistant message content.

4. `transcript_path`:
   - stored only as provenance/recovery metadata;
   - path traversal and external absolute paths are rejected or sanitized;
   - undocumented transcript parsing is not canonical input.

## 8. Security tests

| Threat | Required check |
|---|---|
| Missing/invalid Runtime bearer token | `/event` returns unauthorized and writes no raw record |
| Forged project root | cannot route into another project |
| Session/project mismatch | raw forensic record may remain, but project/Ledger/chat sinks are blocked |
| Oversized HTTP payload | safe rejection, no partial raw/index/checkpoint writes |
| Raw path escape | all raw/blob/error paths remain under workplace runtime root |
| Poisoned duplicate | quarantined privately, no derived effects |
| Operator diagnostics | no raw payload, chat content, token or secret-rich field is logged |
| Malformed JSON | rejected before durable receipt |
| Symlink/path traversal in blob/ref handling | no write outside runtime root |

## 9. Privacy and release validation

Required gates:

1. Runtime raw/chat/error data is not tracked by git.
2. Release archive contains Core code and schemas, not workplace raw journal, blobs, transcripts, checkpoints, indexes or private errors.
3. Public cleanliness checks do not print or publish raw/chat contents.
4. Outbound hooks do not receive raw/chat content unless an explicit export path requests sanitized/full content.
5. `events-validate` remains structural runtime/chat NDJSON validation; schema validation remains a separate release gate.
6. Public artifacts use contract path shapes only, not private absolute workplace paths.

## 10. Performance smoke

Measure, do not optimize blindly.

Baseline inputs:

```text
10_000 events
at least 3 sessions
at least 2 projects
parallel writers
mixed known/unknown events
large payload sample
```

Metrics:

- raw append latency p50/p95;
- duplicate receipt latency;
- memory at Runtime startup;
- replay duration by session;
- project routing throughput;
- index/checkpoint write latency;
- maximum raw shard size in the run;
- error/quarantine path cost.

Pass condition for first slice: no unbounded memory growth, no corrupt NDJSON, no cross-project writes, and replay finishes missing-only routing on the synthetic baseline.

## 11. Suggested execution order

1. Add characterization tests for current Codex/Runtime/Ledger behavior before implementation.
2. Implement raw envelope/journal/index behind Core ingress.
3. Add raw capture and malformed/oversized tests.
4. Switch Runtime `/event` and fallback to the same Core path; run equivalence tests.
5. Switch Codex adapter to raw native envelope; run legacy semantics tests.
6. Add idempotency, conflict and crash-after-raw tests.
7. Add replay smoke for one session.
8. Add chat automatic capture tests only for provider events with real content.
9. Add security/privacy/release gates.
10. Run concurrency/performance smoke.
11. Require independent code review focused on raw-first order, adapter thinness, cross-project routing, duplicate sinks, operator log privacy and replay idempotency.

## 12. Minimum pass criteria for first slice

The first slice is acceptable only if all are true:

- raw durable append happens before normalization/routing;
- Runtime and fallback use one Core ingress;
- existing supported Codex normalized semantics are preserved;
- unknown native Codex events are raw-captured and not lost;
- duplicate delivery does not duplicate raw, project, Ledger or chat derived records;
- session/project mismatch cannot contaminate another project;
- replay after raw append completes missing derived effects without duplicates;
- concurrent writers cannot corrupt raw NDJSON, indexes or checkpoints;
- manual chat behavior remains compatible;
- automatic chat capture is deterministic and uses the existing transcript model;
- raw/chat private data stays out of release/public artifacts and operator logs;
- `git diff --check`, focused tests, replay smoke, security/privacy checks and release gates pass or have a documented environment-only blocker.
