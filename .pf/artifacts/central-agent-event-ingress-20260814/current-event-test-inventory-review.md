# Независимое ревью `current-event-test-inventory.md`

## Итог
Исходный инвентарь в целом верно находит основные точки покрытия `/event`-ingress, но содержит несколько существенных неточностей и расширительных формулировок. Главные ошибки относятся к текущему маппингу Codex hooks, механике session-routing в host и роли `events-validate`.

## Существенные коррекции
1. Утверждение о маппинге Codex hooks устарело.
Подтверждённый код в `tools/pf_runtime/codex_hooks.py:21-25,46-70` маппит только:
- `SessionStart`: `startup -> agent.session.started`, `resume -> agent.session.resumed`, `compact -> agent.session.compacted`
- `SessionEnd`: `default -> agent.session.ended`
- `PostToolUse`: `default -> agent.command.completed`
- Special case: для `PostToolUse` при `tool_name != "Bash"` тип события повышается до `agent.tool.completed`
`Notification`, `Stop`, `SubagentStop`, `PreToolUse` и `message.*` в текущем коде отсутствуют. Неизвестные hook events возвращают `{"status":"ignored"}`.

2. Утверждение о `_find_project_by_session` неверно.
В `tools/pf_runtime/host.py` такой функции нет. Реальная маршрутизация строится через `ledger_session()` (`419-424`), `project_for_session()` (`633-646`) и проверки в `ingest_event()` (`569-599`). Авторизация по project scope выполняется через сравнение `presence.project_id` с routed project и выбрасывает `PermissionError("session is not authorized for requested project_root")`.

3. Утверждение, что `events-validate` проверяет NDJSON “по схеме”, завышено.
`tools/processforge.py:19537-19565` использует локальные валидаторы `validate_event_object()` и `validate_chat_message_object()` (`10453-10482`), а не JSON Schema engine. Полноценная schema-validation живёт отдельно в `tools/validate-process-forge-schemas.py:976-1017`. Следовательно, `events-validate` не “запускает schema validator централизованно”.

4. Три smoke-скрипта ошибочно отнесены к ingress coverage.
- `tools/smoke_agent_director_tick.py:56-70` не инжектирует runtime events.
- `tools/smoke_process_stage_contract_normalization.py:151-159` читает `runtime-host work-state`, но не прогоняет `/event`.
- `tools/smoke_process_supervisor_tick.py:76-89` вообще не касается event ingress.

## Посекционный аудит инвентаря

### 1) Runtime `/event` и базовый поток
- `smoke_runtime_host_poc.py`: подтверждено напрямую. Есть `runtime-host init/event/project-state/status/tick/rebuild-projections` и явная проверка duplicate (`tools/smoke_runtime_host_poc.py:50-112`).
- `smoke_long_lived_runtime.py`: подтверждено напрямую. Есть singleton/restart/crash-recovery, HTTP `POST /event`, `POST /session/register`, `POST /project-state`, `runtime event`, `runtime tick`, 401 без bearer и 400 на oversized body (`tools/smoke_long_lived_runtime.py:154-339`, `tools/pf_runtime/service.py:369-405,449-454`).
- `smoke_runtime_ledger_hooks_mcp.py`: подтверждено частично. Есть `runtime-host event`, `runtime-host project-state`, Codex adapter и MCP/project-state, плюс 401 на `/shutdown`; но это не общий smoke daemon `/event`-ingress (`tools/smoke_runtime_ledger_hooks_mcp.py:47-94`).
- `smoke_stage_projectors.py`: частично. Основной фокус на projections; `runtime-host event` используется только для создания routed session перед `work_state_payload` (`102-121`).
- `smoke_verification_current_work_state.py`: частично. Аналогично, event используется как вспомогательный шаг для чтения current work state (`64-80`).
- Блок про `smoke_agent_director_tick.py`, `smoke_process_stage_contract_normalization.py`, `smoke_process_supervisor_tick.py`: не подтверждён как ingress coverage.

### 2) CLI runtime/hooks
- Регистрация команд `events-validate`, `chat-record`, `chat-export`, `hooks-dispatch` подтверждена (`tools/processforge.py:25863-25902`).
- Формулировка про `events-validate` надо исправить: это structural validator runtime/chat NDJSON, а не JSON Schema runner (`19537-19565`, `10453-10482`).
- Формулировка про release-tests частично верна, но точнее так:
  - `release-test` включает отдельный шаг `schema validation` через `validate-process-forge-schemas.py` (`6561-6563`);
  - и отдельно `events-validate` (`6703-6706`).
  То есть “доказательство покрытия схем” даёт не `events-validate`, а отдельный release step schema validation.

### 3) Codex hooks
- Доставка через `service.runtime_request(..., "/event", ...)` с fallback на `host.ingest_event()` подтверждена (`tools/pf_runtime/codex_hooks.py:87-107`).
- `smoke_runtime_ledger_hooks_mcp.py` действительно запускает адаптер с `PostToolUse` и проверяет `status == "delivered"` (`59-64`).
- В этом smoke используется `tool_name: "Bash"`, значит ожидаемый event type после normalizer остаётся `agent.command.completed`, а не `agent.tool.completed`.

### 4) Journaling / durable / duplicate
- `event_exists()`, append в durable event log через `core.append_process_event()`, rebuild projection/stage projection подтверждены (`tools/pf_runtime/host.py:348-355,500-543,590-598`).
- Duplicate coverage в `smoke_runtime_host_poc.py` и `smoke_long_lived_runtime.py` подтверждена.
- `smoke_agent_ledger.py` подтверждает durability agent-ledger, но это косвенное доказательство lifecycle journaling, не `/event`-ingress (`31-48`).

### 5) Session mapping / project authorization
- Суть раздела подтверждена, но ссылка на функцию неправильная. Правильные точки: `ledger_session`, `project_for_session`, `project_state_payload`, `ingest_event` (`tools/pf_runtime/host.py:419-424,569-599,633-660`).
- `smoke_runtime_ledger_hooks_mcp.py`, `smoke_runtime_host_poc.py`, `smoke_long_lived_runtime.py` действительно проверяют project isolation и cross-project deny.
- `smoke_single_agent_session_flow.py` и `smoke_multi_project_agent_sessions.py` подтверждают ledger/session isolation, но это скорее косвенное покрытие session ownership, а не `/event`-ingress напрямую.

### 6) Chat transcript recording
- `chat-record` не “пишет в журнал и/или транскрипт”, а делает оба действия: пишет transcript NDJSON и эмитит `chat.message.recorded` через `emit_process_event()` (`tools/processforge.py:10525-10598,19568-19595`).
- `chat-export` читает transcript, пишет outbox JSON в `.pf/runtime/hooks/outbox/wtaicc`, добавляет `session.message.recorded` в event log с `dispatch=False` и затем эмитит `hook.dispatched` (`19605-19636`).
- Schema validator для transcript NDJSON подтверждён в `validate-process-forge-schemas.py:976-1000`.
- Прямого smoke для `chat-record`/`chat-export` не найдено.

### 7) Schema validation / артефакты
- Перечень схем в `validate-process-forge-schemas.py` подтверждён: `event-envelope`, `session-telemetry-event`, `chat-message`, `hook-result`, `wtaicc-outbox-payload` (`266-346,976-1017`).
- Упоминание `runtime-template.schema.json` не подтверждено. В `validate_runtime_json_payloads()` проверяется `templates/runtime/update` против `installed-update-sites.schema.json`, а не `runtime-template.schema.json` (`1002-1017`).
- Утверждение, что `events-validate` “запускает это централизованно”, неверно.
- `smoke_first_run.py` подтверждает bootstrap runtime artifacts и наличие event journal в workplace/project (`72-109,136-154`), но это не самостоятельное покрытие ingress semantics.

## Подтверждённые пробелы
- Нет отдельного smoke для `chat-record` и `chat-export`.
- Нет отдельного smoke, который специально проверяет нормализованный Codex event type `agent.command.completed`/`agent.tool.completed` как целевой инвариант; сейчас это побочный эффект smoke `runtime_ledger_hooks_mcp`.
- Нет выделенного fixture-набора только под `/event`; события в большинстве smoke создаются inline во временных каталогах.
- Нет покрытия для игнорируемых Codex hook events, потому что такие маппинги сейчас вообще не реализованы.
- Нет прямого smoke на `PostToolUse` с не-`Bash` tool, который доказал бы ветку `agent.tool.completed`.
