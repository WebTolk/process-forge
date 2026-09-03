# Инвентаризация текущего тестового покрытия `/event`-ingress

**Задача:** инвентаризация текущих тестов и скриптов без проектирования изменений.

## Что реально покрыто

### 1) Runtime `/event` (host/daemon) и базовый поток событий
- `tools/smoke_runtime_host_poc.py`
  - Покрывает `runtime-host init`, `runtime-host event`, `runtime-host project-state`, `runtime-host status`, `runtime-host tick`, `runtime-host rebuild-projections`.
  - Есть явная проверка дедупликации `event-id duplicate` при отправке того же события дважды.
- `tools/smoke_long_lived_runtime.py`
  - Покрывает `runtime start`, `runtime status`, `runtime session-register`, HTTP `POST /event`, HTTP `POST /session/register`, `runtime event`, `runtime project-state`, `runtime tick`.
  - Проверяет жизненный цикл singleton/restart и устойчивость демона.
  - Есть проверки отказов по безопасности:
    - `/event` без авторизации возвращает 401.
    - `/event` с oversize body возвращает 400.
- `tools/smoke_runtime_ledger_hooks_mcp.py`
  - Покрывает `runtime-host event` в сценарии MCP + проверяет поведение маршрутизации.
- `tools/smoke_stage_projectors.py`
  - Генерирует события через `runtime-host event` и валидирует обновление проекций/состояния.
- `tools/smoke_verification_current_work_state.py`
  - Инициирует `/event` для обновления work-state и проверяет его отражение в текущем состоянии.
- `tools/smoke_agent_director_tick.py`, `tools/smoke_process_stage_contract_normalization.py`, `tools/smoke_process_supervisor_tick.py`
  - Непосредственно затрагивают тик/контрактные шаги пайплайна с инжекцией событий в сценарии оркестрации.

### 2) Команды CLI для runtime/hooks-операций
- В `tools/processforge.py` явно зарегистрированы и доступны:
  - `events-validate`
  - `chat-record`
  - `chat-export`
  - `hooks-dispatch`
- Команда `events-validate` запускает проверку журналов событий и чат-транскриптов по схеме.
- В `release-tests` (там же) `events-validate` включён в smoke-набор, что даёт автоматическое доказательство покрытия схем на этапе релизной проверки.

### 3) Codex hooks (dispatch слоя)
- `tools/pf_runtime/codex_hooks.py`
  - Маппинг `hook_event_name`:
    - `Notification`, `Stop`, `SubagentStop`, `PreToolUse`, `PostToolUse`, а также `message.*`.
  - Отправляет в runtime endpoint `"/event"` через `runtime_request`, с fallback на `host.ingest_event`.
- `tools/smoke_runtime_ledger_hooks_mcp.py`
  - Прямо исполняет этот адаптер с `PostToolUse`.
  - Проверяет статус доставки `"delivered"` для успешного сценария.
  - В том же скрипте есть проверка межпроектного запрета на доставку события.

### 4) Event journaling, дедупликация и durable-поведение
- В `tools/pf_runtime/host.py` реализованы:
  - проверка существования события `event_exists` (дедупликация по id),
  - append в устойчивый журнал,
  - восстановление state через rebuild-пути.
- Параллельные подтверждения в smokes:
  - `tools/smoke_runtime_host_poc.py`: ожидает duplicate-результат на повторном событии.
  - `tools/smoke_long_lived_runtime.py`: ожидает повторное `runtime event` как duplicate.
- `tools/smoke_agent_ledger.py`
  - Проверяет журнал по `agent.checked_in` / `agent.checked_out`, косвенно подтверждая устойчивость и запись lifecycle-событий.

### 5) Маппинг сессий/ledger и авторизация по проекту
- В `tools/pf_runtime/host.py` реализована маршрутизация по активной сессии в `_find_project_by_session`, с проверкой владения/доступа.
- Проверки в smokes:
  - `tools/smoke_runtime_ledger_hooks_mcp.py`
    - отдельные сценарии для проектов `first` и `second`,
    - перезапись/восстановление ledger и `project-state`,
    - запрет cross-project доставки (`not authorized`).
  - `tools/smoke_runtime_host_poc.py`
    - два проекта, разный `project-state` по сессии.
  - `tools/smoke_long_lived_runtime.py`
    - кросс-проектные кейсы: корректный `project-state` по сессиям и 403 при неверном проекте.
  - `tools/smoke_single_agent_session_flow.py`
    - текущая сессия и соотнесение с проектом.
  - `tools/smoke_multi_project_agent_sessions.py`
    - один агент в разных проектах, изоляция checkout-состояний.

### 6) Chat transcript recording
- В `tools/processforge.py`:
  - `chat-record` пишет запись чата в журнал и/или транскрипт.
  - `chat-export` экспортирует transcript.
- В `tools/validate-process-forge-schemas.py`:
  - `chat-message.schema.json` подключена в валидатор.
  - валидируются файлы `runtime/chat/transcripts/*.ndjson`.
- `events-validate` проверяет и валидирует chat-message NDJSON в `command_events_validate`.

### 7) Schema validation / артефакты
- `tools/validate-process-forge-schemas.py` покрывает:
  - runtime event envelope (`event-envelope.schema.json`),
  - session telemetry event schema,
  - chat-message schema,
  - hook-result / outbox payload схемы,
  - валидацию runtime-hook template JSON по `runtime-template.schema.json`.
- `tools/processforge.py`/CLI `events-validate` запускает это централизованно.
- `tools/smoke_first_run.py` и связанные smoke scripts проверяют наличие bootstrap-артефактов runtime, включая событийный журнал в workplace-реквизитах.

## Наблюдаемые пробелы

- Нет отдельного smoke, явно и изолированно проверяющего `chat-record`/`chat-export` через HTTP/API в стиле runtime ingress flow.
- Нет явного smoke с инвариантом “запись/валидация конкретного `agent.command.completed`-события из Codex hooks” как самостоятельной цели (есть только общий PostToolUse + cross-project авторизация).
- Нет отдельной fixture-набор директории, посвящённой только `/event` (события, как правило, создаются инлайн во временных директориях smoke-скриптов).
