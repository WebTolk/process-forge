# Runtime correctness: первый срез генеральной линии

- date: `2026-08-14`
- run: `runtime-general-line-20260814`
- assignment: `runtime-correctness-implementation`

## Результат

Первый срез выполнен. PF Runtime остаётся локальным host/IPC слоем и делегирует
маршрутизацию, события, Ledger, Director, Inspector и projections существующему
PF Core. Новый отдельный Runtime Ledger, event store или process engine не создавались.

## Изменения

### Session-bound event isolation

- `host.ingest_event()` теперь проверяет session binding до event ingestion.
- Для известной session canonical project должен совпадать с requested project.
- Неинициализирующее событие неизвестной session отклоняется.
- Только `agent.session.started` и `agent.session.resumed` могут впервые привязать
  session к проекту; последующие события используют уже установленную связь.

### Concurrency и projections

- Добавлен process-local re-entrant lock для Runtime host state,
  event deduplication и projection rebuild.
- Конкурентные `session/register`, event ingestion, tick и status теперь не
  выполняют несериализованный read-modify-write одного cache state.
- Atomic temporary names включают UUID, поэтому независимые записи одного PID
  не используют один и тот же temporary path.

### Liveness/recovery

- Liveness требует и живой PID, и успешный `/readyz` с `ready=true`.
- State с PID чужого/unresponsive процесса и stale lock больше не принимается
  за работающий Runtime; start выполняет stale cleanup и recovery.
- Loopback bearer comparison использует constant-time comparison.

### Windows oversized IPC contract

- Smoke проверяет header-based rejection oversized request без race, когда
  Windows client продолжает потоковую отправку после server-side early reject.
- Сохраняется лимит тела `1 MiB` и предсказуемый `400` для превышения.

## Regression coverage

`smoke_long_lived_runtime.py` дополнительно доказывает:

- event от `session A` в `project B` получает `403`;
- параллельные регистрации не смешивают project bindings;
- stale state с живым чужим PID и недоступным endpoint восстанавливается;
- oversized request получает детерминированный отказ на Windows.

Существующие сценарии singleton, stale dead PID, crash/restart, auth, duplicate
events, two projects, Director/Inspector, active worker recovery и fallback
сохранены.

## Проверки

Прошли:

- `python -m py_compile ...`
- `python tools/smoke_runtime_host_poc.py`
- `python tools/smoke_long_lived_runtime.py`
- `python tools/validate-process-forge-schemas.py --root .`
- `python tools/validate-public-cleanliness.py --root .`
- `python tools/processforge.py events-validate --project-root .`
- `python tools/processforge.py release-test --root . --only smoke_runtime_host_poc --only smoke_long_lived_runtime --fail-fast`
- `git diff --check`

## Остаточные ограничения

- `project-context-check` всё ещё blocked: classification freshness и три
  required capabilities. Поэтому worker capsule/shell-worker независимого review
  пока не запускается.
- Runtime `state.json.sessions` пока остаётся rebuildable cache. Перенос
  canonical session binding к Ledger — следующий Ledger-centric slice.
- Live Codex hook adapter, MCP bridge, projector/stage-owned maintenance и
  checksum inventory не входят в этот срез.
