# Shared Init Rereview

## Вердикт

`pass`: повторная проверка не нашла новых блокирующих замечаний. Две проблемы из предыдущего review закрыты в проверенных границах.

## Findings

Новых `High` / `Medium` findings не обнаружено.

## Подтверждено

- MCP больше не пропускает `answers_path`: для `pf.project_initialization.initialize` и `repair` используется per-tool allowlist, неизвестные аргументы отклоняются как `invalid_arguments` (`tools/pf_runtime/mcp_server.py:86-95`). Smoke также фиксирует попытку передать `answers_path` и ожидает `invalid_arguments` (`tools/smoke_project_init_local_search_mcp.py:91-92`).
- Raw doctor output больше не копируется в публичный `.pf/artifacts/project-onboarding-report.md`: `finalize_project_onboarding_doctor_artifacts()` игнорирует полный `output` и пишет только статус, инструкцию локального запуска doctor и краткие hints (`tools/processforge.py:5748-5769`).
- MCP Ledger-boundary сохранена: tool call требует session, привязывает session к Ledger project через `host.project_for_session()`, а конфликтующий `project_root` отклоняет как `session_project_mismatch` до выполнения initialization/repair (`tools/pf_runtime/mcp_server.py:66-80`). Smoke покрывает mismatch (`tools/smoke_project_init_local_search_mcp.py:68`, `tools/smoke_project_init_local_search_mcp.py:82-83`).
- Exact apply boundary сохранена: Core writer запускается только при `apply_requested is True` (`src/processforge_core/project_initialization.py:71-76`), MCP дополнительно отклоняет отсутствующий/не-true `apply` (`tools/pf_runtime/mcp_server.py:84-85`), smoke покрывает repair без apply (`tools/smoke_project_init_local_search_mcp.py:70`, `tools/smoke_project_init_local_search_mcp.py:86-87`).
- Repair boundary сохранена: repair требует существующий project root с `.pf`, поддерживает только `refresh_context`, а без apply возвращает план без записи (`src/processforge_core/project_initialization.py:132-147`).

## Проверки

- PASS: статический `ast.parse` для `src/processforge_core/project_initialization.py`, `tools/processforge.py`, `tools/pf_runtime/mcp_server.py`, `tools/smoke_project_init_local_search_mcp.py`.
- NOT RUN: полный `tools/smoke_project_init_local_search_mcp.py` не запускался, потому что текущая worker-среда read-only, а smoke создаёт временные проекты и файлы. Read-only ограничение не связано с продуктовым кодом.