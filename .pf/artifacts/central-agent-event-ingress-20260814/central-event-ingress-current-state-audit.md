# Аудит текущего состояния входа событий (центральный ingress)

Дата ревизии: `2026-08-14`
Задача: read-only аудит без рекомендаций по не подтвержденным переписям.

## 1) Наблюдаемые источники записи событий и журналы

- Процессный журнал проекта хранится в `runtime/events/events.ndjson` (в пределах `project_root`) и формируется через `append_process_event(...)` в [tools/processforge.py](/D:/Dev/process-forge/tools/processforge.py).
- `append_process_event(...)` инициализирует запись только если `event_id` ещё не существует в журнале (`event_exists(...)`), то есть дедупликация на уровне журнала обязательна.
- Каждый успешный процессный инкапсулированный event пишет в `.ndjson` через `append_process_event`, после чего вызывает `dispatch_hooks(..., outbox=True)`.
- Сообщения чата пишутся в `runtime/chat/transcripts/<session>.ndjson` и дополнительно эмитируют процессное событие `chat.message.recorded` [tools/processforge.py]( /D:/Dev/process-forge/tools/processforge.py).
- Хуки/исходящие доставки пишутся в:
  - `runtime/hooks/outbox/<hook_name>/...json`
  - `runtime/hooks/results/<delivery_id>.json`
  (через `dispatch_hooks` и `write_hook_result`).

## 2) Единая точка runtime-ingress (`/event`) и fallback-цепочка

- Реальный endpoint ingestion: `POST /event` в runtime-сервисе (`tools/pf_runtime/service.py`), делегирует в `host.ingest_event(...)`.
- Перед этим endpoint требует `Authorization: Bearer <token>`, иначе `401`.
- `codex_hooks.dispatch(...)` пытается отправить событие в runtime через `service.runtime_request("/event", event)`.
- При ошибке runtime-доставки включается fallback: локальный вызов `host.ingest_event(...)` (ledger-fallback path), пометка транспорта в результате.

## 3) Нормализация и идемпотентность

- Входной payload нормализуется в `normalize_event(...)` с валидацией типа события.
- `event_id` детерминированный (`stable_event_id`) по нормализованному содержимому.
- Дедупликация выполняется на двух уровнях:
  - в `host.ingest_event(...)` (проверка `event_exists`),
  - в `append_process_event(...)` при записи в `events.ndjson`.
- Для уже записанных `event_id` возвращается `duplicate=true`, запись не дублируется.

## 4) Каналы авторизации и привязки session/project

- Публичный ingress в runtime защищён bearer-token.
- В `host.ingest_event(...)` активна сессионная проверка:
  - если `session_id` не найден в леджере, разрешён только bootstrap-событие с типом `agent.session.started` или `agent.session.resumed`,
  - для остальных событий в таком случае будет ошибка доступа.
- При известной сессии выполняется проверка соответствия `project_id` сессии и целевого проекта.
- MCP-сервер (`tools/pf_runtime/mcp_server.py`) читающий слой:
  - принимает только session-bound запросы и не пишет события,
  - также применяет `project_for_session` и проверяет, что явный `project_root` не конфликтует с сессией.

## 5) Жизненный цикл в леджере (ledger conversion)

- `host.ingest_event(...)` выполняет `ledger_from_event(...)` для сессионных событий:
  - `agent.session.started` / `agent.session.resumed` → `core.command_agent_checkin`
  - события heartbeat/command/tool-completion → `core.command_agent_heartbeat`
  - `agent.session.ended` / `agent.session.stopped` → `core.command_agent_checkout`
- Эта же логика делает сессионный леджер источником маршрутизации session→project и валидации доступа.

## 6) Хуки: outbox, результаты, ограничения

- Конфиг хуков берётся из `.pf/hooks.yaml`; выборка по `event_types`.
- Для типов `outbox`, `file_outbox`, `webhook`/`webhook_future` при `outbox=True` событие уходит в файловый outbox.
- Для webhook-событий фактическая сетевая доставка не обязателен: при `network_send_enabled=False` действие помечается как skip.
- `hook_type=command` сейчас в dispatch-пути не исполняется (требует отдельный runner/флоу), статус `skipped`.
- Каждая доставка получает отдельный `delivery_id` и результат сериализуется в `runtime/hooks/results`.
- При каждом outbox-доставка формируется/обновляется `hook.dispatched`-событие (без рекурсивного повторного dispatch).

## 7) Проекторные артефакты / rebuild-триггеры

- Есть механизмы проектирования состояний:
  - восстановление `command-history` из `agent.*` событий,
  - сбор `stage-obligations` из деклараций процессов и активных assignment.
- Из текущей архитектуры видно разделение ролей:
  - ingest пишет в журнал/применяет ledger,
  - проекционные артефакты формируются отдельными пересборками, а не как единственный неявный side-effect каждого append-события.
- MCP в текущем виде только читает состояние, не инициирует запись в проекции.

## 8) Итоговая картина (текущее состояние)

- Погружение событий в ядре уже единообразно: нормализация → проверка авторизации/связи session→project → idem‑check → запись в `events.ndjson` + ledger/проекция-запрос + hooks dispatch при конфиге.
- Единый runtime ingress: `/event` (защищённый).
- Надёжность доставки обеспечивается fallback на локальный ingest при ошибках runtime.
- Хуки в текущей реализации по сути file-first (outbox-first), сетевых отправок и command-exec как автопути нет.
