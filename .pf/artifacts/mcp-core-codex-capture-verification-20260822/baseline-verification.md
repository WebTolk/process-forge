# Базовая проверка MCP, Python Core и захвата Codex-сообщений

Дата: 2026-08-22

## Результаты

- `python tools/smoke_runtime_ledger_hooks_mcp.py` — PASS. Проверены
  Ledger-bound маршрутизация, адаптер Codex hooks и stdio MCP, включая
  отклонение межпроектного доступа и несовпадающей сессии.
- `python tools/smoke_conversation_completeness.py` — PASS. Контракт фиксирует
  `UserPromptSubmit`, `Stop` и `SubagentStop`, дедупликацию, хранение чата,
  приватность event-journal и валидацию событий.
- `python tools/smoke_project_init_local_search_mcp.py` — PASS. Python Core
  проверил snapshot-authorized SQLite FTS5 search.
- Установленный beta.2 MCP успешно обработал `initialize` и `tools/list`:
  ProcessForge `1.0.2`, 11 инструментов.
- `codex mcp list` показывает `processforge` в состоянии `enabled` и указывает
  на установленный beta.2 stdio server.

## Подтверждённый разрыв

В корне проекта отсутствует `.codex/hooks.json`. Поэтому текущий сеанс Codex
не может доставлять реальные `UserPromptSubmit`, `Stop` или `SubagentStop` в
ProcessForge, хотя код адаптера и его contract smoke проходят. Следующая
задача должна установить только управляемые project-local hooks, сохранить
резервную копию при необходимости и затем доказать событие и его чтение через
MCP.

## Вне утверждений

Реальный host-level MCP tool call из Codex здесь пока не заявляется: ранее
такой вызов был остановлен политикой host `approval=never` до выполнения
сервера. Данный baseline подтверждает direct stdio и Python contracts.
