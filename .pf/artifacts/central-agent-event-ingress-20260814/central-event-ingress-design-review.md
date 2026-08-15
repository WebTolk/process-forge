# central-event-ingress-design-review

Дата: `2026-08-14`
Итог: `CONDITIONAL PASS` с обязательным blocker перед implementation.

## Blocker

### B1 — не зафиксирован точный idempotency/replay key contract

Статус: `FAIL / BLOCKER`

Архитектура правильно требует dedupe/idempotency до расширения Codex adapter-а (`задания/process-forge-central-agent-event-ingress-master-prompt.md:78-91`) и требует, чтобы повторная delivery не создавала duplicate normalized/chat records (`задания/process-forge-central-agent-event-ingress-master-prompt.md:1574-1577`). Но v2-дизайн пока задаёт только поля receipt (`central-event-ingress-design-v2.md:64-77`), пример `raw_event_id: raw_<hash>` (`event-storage-layout-v2.md:34-52`) и replay-правила для deterministic normalized ids (`event-routing-policy-v2.md:86-92`), не определяя точный состав hash/key, поведение при отсутствии `native_event_id`, collision policy, duplicate raw receipt и deterministic id для chat records.

Текущий код усиливает риск: Codex adapter генерирует pre-normalized `event_id` (`tools/pf_runtime/codex_hooks.py:61-69`), host потом использует `stable_event_id(raw)` для normalized event (`tools/pf_runtime/host.py:457-466`), а ручной chat writer создаёт `message_id` через UUID (`tools/processforge.py:10547`). Без явного нового контракта нельзя доказать эквивалентность Runtime-up/Runtime-down путей и replay без дублей.

Перед implementation нужно добавить в design/routing/storage контракт:
- raw id derivation inputs и fallback при пустом/нестабильном provider id;
- duplicate raw receipt semantics;
- deterministic ids для normalized/project/chat derived records;
- replay rule для уже существующих derived records;
- collision/poisoned duplicate handling.

## Findings

| Область | Статус | Вывод |
|---|---:|---|
| Raw-first durability | `PASS, blocked by B1` | Целевая цепочка задана правильно: provider payload → Core ingress → durable workplace raw append → receipt → normalization/routing (`central-event-ingress-design-v2.md:23-36`). Это соответствует master raw-first invariant (`задания/process-forge-central-agent-event-ingress-master-prompt.md:275-309`). |
| Preservation of current host/Runtime/Codex behavior | `CONDITIONAL PASS` | Дизайн явно сохраняет текущие `SessionStart`, `SessionEnd`, `PostToolUse` mappings (`central-event-ingress-design-v2.md:103-110`) и first-slice characterization (`central-event-ingress-design-v2.md:186-197`). Текущее состояние подтверждает normalized-first путь и ledger/project writes (`tools/pf_runtime/host.py:569-599`, `tools/pf_runtime/codex_hooks.py:46-76`). Условие: first slice не должен делать derived sinks eventually-consistent без отдельного решения, иначе текущие immediate smokes могут регрессировать. |
| Workplace vs project boundary | `PASS` | Полный native stream вынесен на workplace-level (`event-storage-layout-v2.md:5-19`), project journal оставлен filtered derivative `.pf/runtime/events/events.ndjson` (`event-storage-layout-v2.md:75-83`). Это совпадает с master requirement (`задания/process-forge-central-agent-event-ingress-master-prompt.md:54-64`). |
| Schema compatibility | `CONDITIONAL PASS` | Reconciliation верно оставляет `event-envelope.schema.json` canonical для project journal и запрещает развивать `processforge-event` как второй канон (`event-schema-reconciliation.md:3-18`, `event-schema-reconciliation.md:23-29`). Условие: новый `NativeAgentEvent` должен быть отдельным adapter/raw ingress contract, а не новой параллельной canonical project-event schema. |
| Ledger routing | `PASS` | Routing policy сохраняет Ledger как первый источник `session -> project`, блокирует mismatch для project/ledger/chat sinks, но сохраняет raw (`event-routing-policy-v2.md:19-42`). Current host already validates known session project mismatch (`tools/pf_runtime/host.py:581-587`). |
| Unknown native events | `PASS` | Дизайн требует raw capture без project routing до появления политики (`central-event-ingress-design-v2.md:112-120`), routing artifact повторяет raw append/dedupe and pending mapping (`event-routing-policy-v2.md:69-80`). Это закрывает master DoD про unknown future events (`задания/process-forge-central-agent-event-ingress-master-prompt.md:1561-1563`). |
| Concurrency/storage scale | `CONDITIONAL PASS` | Storage layout вводит hourly shards, indexes, checkpoints, blob policy и явно требует interprocess lock/atomic strategy (`event-storage-layout-v2.md:21-61`, `event-storage-layout-v2.md:95-142`). Это покрывает master sharding/concurrency requirements (`задания/process-forge-central-agent-event-ingress-master-prompt.md:351-376`). Условие: implementation не может использовать только текущий `threading.RLock`, который ограничен одним процессом (`tools/pf_runtime/host.py:23-31`). |
| Replay | `CONDITIONAL PASS` | Replay dimensions и checkpoints заданы (`event-storage-layout-v2.md:112-132`), routing rules требуют deterministic derived ids and missing-only routing (`event-routing-policy-v2.md:82-92`). Условие остаётся B1: без точного id contract replay нельзя считать implementable. |
| Chat first-class and privacy | `CONDITIONAL PASS` | Дизайн переиспользует существующий transcript layout, `chat.message.recorded` как metadata event и запрещает `ChatLog` duplicate (`central-event-ingress-design-v2.md:122-142`). Текущий writer действительно пишет transcript и metadata event с `content_ref`/`content_hash` (`tools/processforge.py:10525-10598`). Условие: automatic capture должен получить deterministic dedupe для repeated provider message delivery. |
| Offline fallback equivalence | `CONDITIONAL PASS` | Дизайн требует Runtime `/event` и direct fallback через один Core ingress (`central-event-ingress-design-v2.md:156-168`), routing требует same raw journal and same idempotency keys (`event-routing-policy-v2.md:82-85`). Условие зависит от B1. Текущий fallback пока вызывает `host.ingest_event(...)` normalized-first (`tools/pf_runtime/codex_hooks.py:87-107`). |
| Security/privacy/release boundary | `PASS` | Routing artifact явно запрещает tracking/release/public/operator-log для raw/chat streams (`event-routing-policy-v2.md:94-104`), master требует security and release/privacy tests (`задания/process-forge-central-agent-event-ingress-master-prompt.md:1388-1407`). Current release command set already has public cleanliness and events validation gates, but future raw/chat absence test still must be added (`tools/processforge.py:6559-6706`). |
| Minimal slice scope | `PASS` | Implementation sequence matches master first slice and excludes full work-state/projectors migration (`central-event-ingress-design-v2.md:186-197`, `задания/process-forge-central-agent-event-ingress-master-prompt.md:1257-1273`). |

## Decision

Implementation should not start until B1 is resolved in the planning artifacts. After that, the architecture is acceptable for a narrow first slice: Core raw ingress, workplace raw journal, Runtime/fallback delegation, Codex adapter switch, preservation of current normalized semantics, raw capture of confirmed native events, limited chat capture where provider content exists, and one-session replay smoke.
