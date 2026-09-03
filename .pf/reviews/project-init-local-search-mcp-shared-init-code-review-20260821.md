# Shared Init Code Review

## Вердикт

`fail`: реализация в целом следует shared-service модели, но есть два риска, которые нужно закрыть перед принятием.

## Findings

### High: MCP initialize принимает невалидированные extra arguments и может читать произвольный `answers_path`

`tools/pf_runtime/mcp_server.py:84-88` проверяет только `apply`, затем делает `request = dict(arguments)` и передает весь payload дальше. `respond()` также не валидирует `arguments` по schema (`tools/pf_runtime/mcp_server.py:162-166`). В shared service `src/processforge_core/project_initialization.py:87-88` затем читается `answers_path`, хотя MCP schema его не объявляет (`tools/pf_runtime/mcp_server.py:133-134`).

Последствия:

- MCP-клиент с `apply: true` может заставить сервер читать server-local файл как answers-файл вне Ledger/workspace resource boundary.
- При missing/invalid `answers_path` `tools/processforge.py:1368-1375` бросает `SystemExit`, а MCP ловит только `ProjectInitializationError`/`Exception`; `SystemExit` может завершить stdio MCP server вместо safe error.
- Это нарушает заявленный контракт controlled MCP boundary из `docs/concepts/runtime-mcp.md:17-21`.

Рекомендация: для MCP init собирать request по allowlist, не переносить `answers_path`, отклонять неизвестные ключи фактической runtime-валидацией, а loader/normalization ошибки конвертировать в safe `SessionReadError`.

### Medium: repair пишет raw doctor output в публичный onboarding report

`tools/processforge.py:5811-5816` в `execute_project_repair()` вызывает `finalize_project_onboarding_doctor_artifacts()`. Эта функция пишет полный `doctor_output` в публичный `.pf/artifacts/project-onboarding-report.md` (`tools/processforge.py:5748-5769`). `run_command_capture()` включает в этот output текст `SystemExit` (`tools/processforge.py:2679-2689`).

Да, текущий `command_doctor_project()` в основном формирует относительные сообщения, но это не является общей гарантией для всех future/error branches. Поэтому repair, который заявлен как deterministic refresh-only, получает побочный эффект: публичный артефакт может сохранить raw diagnostic text с локальными путями или деталями среды. Это расходится с заявлением отчета реализации, что MCP не возвращает doctor output/private paths (`.pf/artifacts/project-init-local-search-mcp-20260821/shared-init-implementation-report.md:23-24`); проблема не в response, а в публичном artifact side effect.

Рекомендация: писать в публичный onboarding report только redacted summary/status, а raw doctor output складывать в private runtime/log artifact либо прогонять через тот же public path/secret redaction gate перед записью.

## Подтверждено без замечаний

- CLI `project-onboard` идет через общий сервис: `tools/processforge.py:5836-5857`.
- MCP initialize/repair делегируют в тот же `project_initialization` service: `tools/pf_runtime/mcp_server.py:81-95`.
- Exact boolean `apply` guard есть в Core (`src/processforge_core/project_initialization.py:71-76`) и дополнительно в MCP (`tools/pf_runtime/mcp_server.py:84-85`).
- Repair не делает onboarding для отсутствующего `.pf`: `src/processforge_core/project_initialization.py:132-147`.
- Brownfield non-overwrite сохранен через candidate-файлы без `force`: `tools/processforge.py:1442-1454`, `.gitignore` аналогично `tools/processforge.py:1457-1473`.
- `resolve_workspace_path_ref()` блокирует escape через `relative_to()` для package и registry roots: `tools/processforge.py:9189-9237`.

## Проверки

- PASS: AST parse для `project_initialization.py`, `processforge.py`, `mcp_server.py`, `smoke_project_init_local_search_mcp.py`.
- PASS: in-memory проверка exact `apply is True`; строка `"true"` не вызывает writer.
- BLOCKED: полный `tools/smoke_project_init_local_search_mcp.py` не выполнен из-за запрета создания временной директории в текущем read-only окружении. Продуктовый код не изменялся.