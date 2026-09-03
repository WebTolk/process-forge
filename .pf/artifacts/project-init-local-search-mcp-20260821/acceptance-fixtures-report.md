# acceptance-fixtures-report

## Статус

`blocked`: acceptance smoke не создан и не записан, потому что текущий filesystem-профиль разрешает только чтение. В рамках assignment нельзя безопасно выполнить требуемые изменения в `tools/smoke_project_init_acceptance.py` и записать `.pf/artifacts/project-init-local-search-mcp-20260821/acceptance-fixtures-report.md`.

## Что проверено

- `tools/smoke_project_init_acceptance.py` отсутствует.
- `tools/smoke_project_init_local_search_mcp.py` уже покрывает часть прежнего сценария: `pf.search`, snapshot authorization, `current`/`stale`, MCP `tools/list`, session binding, apply-gate для repair, успешный repair, запрет лишних аргументов, template search и отсутствие приватных путей в публичном onboarding report.
- `src/processforge_core/project_initialization.py` поддерживает явные `platforms`, `specializations`, `process` в `_initialization_request()` и deterministic `repair_project()`.
- `src/processforge_core/local_resource_search.py` реализует статусы `empty`, `current`, `stale`, `search_unavailable`, но существующий smoke фактически проверяет только `current` и `stale`.
- `tools/pf_runtime/mcp_server.py` публикует `pf.session_context`, `pf.project_initialization.*`, `pf.search`.
- `tools/pf_runtime/session_read.py` возвращает `work.stage_id` и `work.stage_obligations` через `host.stage_obligations_payload()`.

## Запуск проверки

Команда:

```powershell
python tools/smoke_project_init_local_search_mcp.py
```

Результат: не дошла до продуктовых assertions. Исполнение остановилось на создании временной fixture-директории с `PermissionError [WinError 5]`. Это блокер текущей read-only среды выполнения, а не подтвержденный дефект ProcessForge.

## Непокрытые требования assignment

Не удалось добавить и доказать новый isolated executable acceptance smoke для:

- complete initialization с явными `platform`, `specialization`, `process`;
- interrupted-init repair preservation;
- всех FTS lifecycle статусов: `empty`, `current`, `stale`, `search_unavailable`;
- `pf.session_context` stage obligations после реального stage change.

## Ограничения

- Файлы не изменялись.
- Сабагенты не запускались: `subagent_policy.allow=false`.
- Live Codex UI verification и release archive validation не выполнялись, как и требовалось assignment.