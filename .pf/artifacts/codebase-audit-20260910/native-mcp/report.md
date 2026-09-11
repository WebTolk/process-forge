# Native MCP/session binding audit

Дата: 2026-09-10  
HEAD: `901d0551773fe7a5b382b89ebe95b212b0747e83`  
Область: `tools/pf_runtime/mcp_server.py`, `tools/pf_runtime/session_read.py` и
необходимый для трассировки Core lookup.  Product-код не изменялся.

Проба: [probe_mcp_native.py](probe_mcp_native.py). Она создаёт workplace и
ProcessForge project в системном временном каталоге, выполняет реальный
`workplace-init`, `project-onboard`, `agent-checkin`, затем запускает
`tools/pf_runtime/mcp_server.py` отдельным subprocess. Захваченный вывод:
[probe_mcp_native.out](probe_mcp_native.out).

## F-01 — opaque session ids теряют identity при lookup и persistence

Severity: P2 (блокирует все session-scoped MCP views и Forge tools для части
допустимых provider session ids).  Complexity: M. Рекомендуемая junior-модель:
`gpt-5.3-codex-spark`.

Точки: `tools/pf_runtime/mcp_server.py:67-91` сохраняет переданный id и
передаёт его в `session_read`; `tools/pf_runtime/session_read.py:43-69`
вызывает `core.find_agent_presence(..., session_id=session_id)`. В Core
`tools/processforge.py:17084-17085` путь presence строится через lossy
`safe_id`, а на `17137-17148` lookup также преобразует только вход и затем
сравнивает его с сохранённым значением. При этом `command_agent_checkin` на
`tools/processforge.py:17263-17275` сохраняет `args.session` без этой
канонизации.

Контракт не ограничивает `session_id` безопасным lowercase-форматом: схема
`schemas/agent-presence.schema.json:10` требует только string, а модель
описывает session id как идентичность конкретного запуска/окна
(`docs/ru/concepts/agent-session-model.md:94-102`). Поэтому `Case-Session` и
`case-session` должны оставаться двумя различными opaque identities.

Триггер пользователя: provider/operator передаёт session id с заглавной
буквой (например `Case-Session`), что CLI принимает. После успешного
`agent-checkin` тот же exact id передаётся MCP через `--session`. Отдельный
триггер — два check-in одного agent с `Case-Session` и `case-session`.

Ожидается: `pf.session_context` возвращает проекцию привязанной к проекту
сессии, поскольку check-in записал именно этот id и тот же id используется в
MCP-процессе.

Факт: после одиночного check-in MCP отвечает `isError: true`,
`tool_error_code: unknown_session`. После двух check-in остаётся один
presence-файл с `session_id: case-session` (`expected_presence_count: 2`,
`actual_presence_count: 1`), при этом оба lookup (`Case-Session` и
`case-session`) возвращают успех и тем самым используют одну identity. Это
видно в `probe_mcp_native.out:81-115`. Запуск:

```powershell
python .pf/artifacts/codebase-audit-20260910/native-mcp/probe_mcp_native.py
```

Минимальное исправление: сохранить session id как exact opaque identity при
check-in и lookup. Для приватных путей использовать collision-resistant
encoding или digest от полного id с проверкой обратного соответствия; нельзя
исправлять это простой потерей регистра/символов. Исправление должно покрыть
общий Core lookup, чтобы одинаково заработали `pf.session_context`,
`pf.session_chat`, `pf.session_activity` и `host.project_for_session`.

Acceptance:

1. Реальный check-in с `Case-Session` и MCP с тем же id возвращает успешный
   `pf.session_context`.
2. Одновременные check-in `Case-Session` и `case-session` дают две presence
   записи, и каждый exact lookup возвращает свою запись.
3. Чат и activity для каждого opaque id читаются из правильного project root.
4. Существующие lowercase ids сохраняют текущий успешный путь.

## F-02 — stdio facade нарушает envelope/notification semantics JSON-RPC

Severity: P2 (интероперабельность MCP; malformed calls получают
неправильный business error). Complexity: S. Рекомендуемая junior-модель:
`gpt-5.3-codex-spark`.

Точки: `tools/pf_runtime/mcp_server.py:290-308` читает `method` и `id`, но не
проверяет `jsonrpc == "2.0"`, наличие корректного request envelope или
отсутствие id для notification. На `:301-304` любой не-словарь `params` или
`arguments` сводится к `{}` вместо `-32602`.

Подтверждены четыре входа из того же subprocess probe, включая два корректных
JSON-RPC 2.0 notifications:

| Вход | Ожидается | Факт |
| --- | --- | --- |
| `{"jsonrpc":"2.0","method":"tools/list"}` без `id` | notification, stdout пуст | ответ с `id: null`, `isError: false` |
| `{"jsonrpc":"2.0","method":"tools/call",...}` без `id` | notification, stdout пуст | ответ с `id: null`, `isError: false` |
| `{"jsonrpc":"1.0","id":2,"method":"tools/list"}` | `-32600 Invalid Request` | успешный `tools/list`, переписан в `jsonrpc: 2.0` |
| `tools/call` с `params.arguments: []` | `-32602 Invalid params` | business error `missing_project_root` |

Компактное evidence в `probe_mcp_native.out:27-49`: ожидались counts
`[0, 0, 1, 1]` и всего 2 ответа, фактически получены `[1, 1, 1, 1]` и 4
ответа; первые два имеют `id: null`, третий — `jsonrpc: 2.0` при входе
`1.0`, четвёртый — `tool_error_code: missing_project_root`.

Минимальное исправление: добавить bounded JSON-RPC envelope validation перед
dispatch; для отсутствующего `id` не писать response; для неверной версии,
невалидного request и неверной формы `params/arguments` возвращать стандартные
`-32600`/`-32602` с сохранением request id только там, где он валиден.

Acceptance:

1. Notification `tools/list` и notification `tools/call` не создают stdout.
2. Версия, отличная от `2.0`, и объект без `method` дают `-32600`.
3. Необъектные `params`/`arguments` дают `-32602`, не `missing_project_root`
   и не внутренний PF error.
4. Валидные `initialize`, `tools/list` и `tools/call` сохраняют текущие
   ответы; malformed JSON по-прежнему даёт `-32700` из `main`.

## Границы и остаточные риски

Проверка ограничена native stdio facade и session read binding. HTTP Runtime,
`garage.py`, worker collection и уже закрытый F01 search authorization в этот
проход не включались. Никаких governance-файлов и product sources не менялось.
