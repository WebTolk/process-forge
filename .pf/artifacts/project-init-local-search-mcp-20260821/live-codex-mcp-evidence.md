# live-codex-mcp-evidence

Дата проверки: 2026-08-21  
Задача: `project-init-local-search-mcp-live-mcp-evidence-20260821`

## Статус

**Финальный live proof для Codex-first поведения не подтверждён.**

Подтверждено только следующее:

- на машине доступен Codex CLI;
- в Codex CLI есть MCP-регистр;
- продуктовый stdio MCP-фасад ProcessForge локально умеет объявить `pf.search`;
- ProcessForge/pf MCP-сервер сейчас не зарегистрирован в видимом `codex mcp list`;
- live `pf.search` call в текущем worker-контексте не может быть выполнен без Ledger-bound session.

## Проверенная evidence

1. `codex --version` отработал успешно: `codex-cli 0.148.0`.

2. `codex mcp list` отработал успешно и показал зарегистрированные MCP-серверы: `chrome_devtools`, `context7`, `node_repl`, `playwright`, `serena`, `phpstorm`.

3. В списке `codex mcp list` **нет** ProcessForge MCP-сервера и нет pf-сервера.

4. Именованные проверки подтвердили отсутствие регистрации:
   - `codex mcp get processforge` -> `No MCP server named 'processforge' found`;
   - `codex mcp get pf` -> `No MCP server named 'pf' found`;
   - `codex mcp get process-forge` -> `No MCP server named 'process-forge' found`.

5. Прямой read-only stdio запуск `tools/pf_runtime/mcp_server.py` с `initialize` + `tools/list` успешно вернул сервер `processforge` версии `1.0.2` и список tools, включая:
   - `pf.project_state`;
   - `pf.project_initialization.status`;
   - `pf.project_initialization.initialize`;
   - `pf.project_initialization.repair`;
   - `pf.work_state`;
   - `pf.resolve`;
   - `pf.search`;
   - `pf.workplace_state`;
   - `pf.session_context`;
   - `pf.session_chat`;
   - `pf.session_activity`.

6. Контролируемый non-mutating `tools/call` к `pf.search` без session не выполнил поиск и вернул безопасную ошибку:
   - `{"error": {"code": "missing_session"}}`.

7. Переменная окружения `PF_MCP_SESSION_ID` в текущем worker-сеансе отсутствует.

## Сопоставление с ранее разрешёнными артефактами

`codex-mcp-tool-visibility-audit.md` фиксировал, что required live gates должны оставаться отдельными: registry configured, Codex sees the server, `tools/list` sees the tool, Ledger-bound safe call.

Текущая проверка закрывает только raw stdio `tools/list` для продуктового сервера. Она **не** закрывает Codex registry visibility, потому что `codex mcp list` не содержит ProcessForge/pf server.

`project-init-local-search-mcp-final-acceptance-review-20260821.md` ранее указывал, что Codex behavior / live MCP visibility не доказаны. По текущей live-проверке этот блокер остаётся актуальным.

## Не подтверждено

- Не подтверждено, что Codex-клиент видит ProcessForge MCP-сервер.
- Не подтверждено, что `/mcp` или `/hooks` в активной Codex-сессии показывают ProcessForge MCP.
- Не подтверждено, что Codex может вызвать `pf.search` как зарегистрированный MCP tool.
- Не подтверждено Codex-first поведение, то есть приоритет `pf.search` перед Context7/web/global workplace search.
- Не подтверждён Ledger-bound успешный `pf.search` call, потому что в текущем worker-контексте нет доступной session binding.

## Вывод

На этой машине есть рабочий Codex MCP registry и локально рабочий ProcessForge stdio MCP-фасад с `pf.search`, но **нет доказательства реальной Codex-регистрации ProcessForge MCP**. Более того, live CLI-проверка прямо показывает, что ProcessForge/pf server сейчас отсутствует в `codex mcp list`.

Точный следующий шаг: зарегистрировать ProcessForge MCP-сервер в Codex-конфигурации, перезапустить или переподключить Codex-клиент, затем повторить gates в таком порядке: `codex mcp list`, active `/mcp`, raw `tools/list` через зарегистрированный сервер, Ledger-bound safe `pf.search` call, отдельный Codex-first behavior сценарий.