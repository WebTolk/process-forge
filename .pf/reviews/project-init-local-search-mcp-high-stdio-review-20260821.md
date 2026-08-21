# high-stdio-review

## Итог

Статус: **не готово к закрытию без доработки**.

Проверка выполнена статическим чтением разрешённых файлов. Запуск `tools/smoke_project_init_local_search_mcp.py` был заблокирован текущим read-only sandbox: `PermissionError` при создании временного каталога `D:\temp\...`.

## Findings

### HIGH: `path_ref.relative_path` может вывести `pf.search` за пределы разрешённого корня

В `tools/processforge.py:9175-9179` и `tools/processforge.py:9197-9199` `resolve_workspace_path_ref()` строит `candidate = (base / relative_path).resolve()`, но не проверяет, что итоговый путь остался внутри `base`. Для абсолютного `relative_path` или `../..` traversal путь может разрешиться вне package/registry root, если он существует.

Дальше `tools/pf_runtime/mcp_server.py:91-100` доверяет этому результату и добавляет его как `content_roots` в runtime-only snapshot, а `src/processforge_core/local_resource_search.py:93-113` индексирует любой явно переданный root. Это нарушает границу snapshot-authorized поиска: snapshot остаётся metadata-only публично, но runtime-разрешение может авторизовать не тот filesystem root.

Рекомендация: после `resolve()` проверять `candidate.relative_to(base.resolve())` для package и registry веток; при выходе за пределы base возвращать `unresolved`/`invalid_path_ref`.

### MEDIUM: stdio smoke не проверяет реальный `pf.search` через MCP

`tools/smoke_project_init_local_search_mcp.py:51-57` проверяет `initialize`, наличие `pf.search` в `tools/list` и `session_project_mismatch` для `pf.project_initialization.status`, но не вызывает `pf.search`.

Из-за этого smoke не покрывает самый рискованный путь текущей реализации: fresh snapshot gate, private `path_ref` resolution в `tools/pf_runtime/mcp_server.py:86-102`, отсутствие абсолютных путей в ответе и корректную обработку ошибок поиска через stdio.

Рекомендация: добавить stdio `tools/call` для `pf.search` на временном resource с `path_ref`, проверить найденный результат, отсутствие абсолютных путей в JSON-ответе и отдельный negative case для stale/missing snapshot.

### LOW: mismatch assertion неполная

`tools/smoke_project_init_local_search_mcp.py:57` проверяет только код ошибки внутри `content[0].text`, но не проверяет `isError == true`. Если сервер начнёт возвращать ошибочный payload как успешный tool result, smoke это частично пропустит.

Рекомендация: дополнительно assert `responses[2]["result"]["isError"] is True`.

## Подтверждённые положительные проверки

- Fixture isolation в core-smoke есть: разрешённый файл лежит в `allowed`, sibling `outside.md` с `forbidden-secret-token` не находится (`tools/smoke_project_init_local_search_mcp.py:18-32`).
- Ledger mismatch для non-session tools реализован перед dispatch: session сначала связывается через `host.project_for_session`, затем conflicting `project_root` отклоняется как `session_project_mismatch` (`tools/pf_runtime/mcp_server.py:64-72`).
- Public metadata-only producer не пишет физические пути в `local_search_resources`: в snapshot попадают `id`, `package_id`, `kind`, `path_ref`, `status`, политики, но не `resolved_path`/`content_roots` (`tools/processforge.py:9741-9754`).
- Runtime-only content root не сохраняется обратно в публичный snapshot: MCP делает `copy.deepcopy(snapshot)` и добавляет `content_roots` только в локальную копию запроса (`tools/pf_runtime/mcp_server.py:89-100`).