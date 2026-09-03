# Idempotency and Replay Review

Дата: `2026-08-14`
Задача: `central-ingress-idempotency-review-20260814`
Итог: `CONDITIONAL PASS`
Режим: planning-only, без изменений кода или design artifacts.

## Вывод

B1 в целом закрыт на уровне planning contract: `idempotency-and-replay-contract.md` фиксирует deterministic raw identity, fallback без provider id, duplicate raw receipt, collision/quarantine policy, deterministic derived keys, replay missing-only, Runtime/direct fallback equivalence и совместимость с текущими Codex/chat semantics.

Implementation may proceed, но с обязательным уточнением для implementation slice: poisoned duplicate с тем же stable provider native identity и другим payload hash нельзя надежно обнаружить только через `raw_event_id` index, потому что `raw_event_id` включает `raw_payload_hash`. Реализация должна завести или явно материализовать дополнительный native-identity key/index без payload hash для conflict detection.

## Findings

| Область | Статус | Вывод |
|---|---:|---|
| Canonical identity serialization | `PASS` | Контракт задаёт NFC, recursive sorted keys, preserved nulls, provider-order arrays, UTF-8 без insignificant whitespace и исключает transport/runtime/local diagnostics из identity. Это достаточно для deterministic `raw_event_id`. |
| Provider-native-id fallback | `PASS` | Приоритет native id задан корректно: stable provider id используется только при declared stability/scope; blank/unstable/adapter-generated id уходит в `payload_fallback`. Legacy `codex:{hook}:...` явно не считается raw native id. |
| False-positive / collision behavior | `CONDITIONAL PASS` | Quarantine policy для `native_id_payload_conflict`, `raw_event_id_hash_collision` и malformed/oversized случаев задана. Условие: для poisoned duplicate нужен индекс stable native identity без `raw_payload_hash`; иначе конфликт с тем же native id, но другим payload получит другой `raw_event_id` и может пройти как новый факт. |
| Duplicate raw receipt | `PASS` | Повтор с тем же `raw_event_id`, `identity_hash` и `raw_payload_hash` возвращает original `raw_location`, не пишет вторую raw line и запускает missing-only repair. Это закрывает crash после raw append до routing. |
| Deterministic project derived keys | `PASS` | `normalized_event_id` и `project_event_idempotency_key` детерминированы через `raw_event_id`, processor identity/version и semantic target. |
| Deterministic Ledger keys | `PASS` | Ledger effect вынесен из raw identity в derived effect с key по `effect_kind/project/session/normalized_event_id`, что сохраняет no-duplicate behavior текущего host. |
| Deterministic chat keys | `PASS` | Automatic provider chat получает deterministic `chat_message_id`, `chat_message_key` и `chat_event_key`; repeated delivery не должна создавать вторую transcript line. |
| Legacy Codex IDs | `PASS` | Контракт явно сохраняет текущую схему `codex:{hook}:{session_id}:{turn_id}:{tool_use_id}` -> `evt_<sha256(...)[:32]>` для `SessionStart`, `SessionEnd`, `PostToolUse`. |
| Manual chat compatibility | `PASS` | Ручной `chat-record` с `msg_<uuid>` сохраняется, как и существующий transcript layout и `chat.message.recorded` metadata event с private privacy. |
| Runtime vs direct fallback equivalence | `PASS` | Оба transport path должны вызывать один Core ingress и давать один `raw_event_id`, derived ids, keys и routing decisions при одинаковом provider payload. Это исправляет текущий split `runtime_request("/event")` / `host.ingest_event(...)`. |
| Replay checkpoint atomicity | `CONDITIONAL PASS` | Replay rule корректен: raw не переписывается, derived effects missing-only, checkpoint продвигается только после present/skipped/deferred/quarantined. Условие реализации: checkpoints/indexes должны писаться temp-file + atomic rename, как требует storage layout. |
| Privacy | `PASS` | Raw/chat streams остаются private runtime data, не попадают в git, release/public artifacts, outbound hooks и operator diagnostics; poisoned/collision payloads также направлены в private runtime errors. |

## Decision

`B1` можно считать resolved at design level. Implementation may proceed for the first slice при выполнении двух обязательных условий:

1. Добавить явный native-identity conflict index/key без `raw_payload_hash` для poisoned duplicate detection.
2. Реализовать checkpoint/index writes атомарно и межпроцессно безопасно, не ограничиваясь текущим in-process `RLock`.

Без этих условий B1 снова станет implementation blocker, даже при корректном тексте основного контракта.
