# Assurance audit: local search MCP

Статус: область достаточна для аудита insertion points и fixture-плана. Продуктовые файлы не изменялись, тесты не запускались.

## Проверенные источники

- `tools/processforge.py`
- `src/processforge_core/local_resource_search.py`
- `tools/pf_runtime/mcp_server.py`
- `tools/pf_runtime/session_read.py`
- `tools/smoke_project_init_local_search_mcp.py`
- `.pf/artifacts/project-init-local-search-mcp-20260821/review-remediation-report.md`

## Вывод

Открытыми остаются ровно зоны, отмеченные remediation-отчётом: metadata-first `local_search_resources` producer, полный lifecycle `empty/current/stale/unavailable`, и Ledger-bound stdio MCP smoke. Текущий код уже содержит часть consumer/MCP основы, но release acceptance преждевременен без этих фикстур.

## Source insertion points

1. Snapshot producer

- Consumer уже ожидает top-level `snapshot.local_search_resources`: `src/processforge_core/local_resource_search.py:75-83`.
- Snapshot builder сейчас формирует `resolved.knowledge_resources` и `resolved.available_knowledge_resources`, но не публикует `local_search_resources`: `tools/processforge.py:9739-9740`, `tools/processforge.py:9845-9856`.
- Ресурсная нормализация уже сохраняет публичный `path_ref`: `tools/processforge.py:8225-8253`, `tools/processforge.py:8658-8685`.
- Приватное раскрытие `path_ref` уже есть и не должно попадать в публичный snapshot как absolute path: `tools/processforge.py:9160-9199`.

Минимальная вставка: добавить helper рядом с `resolve_workspace_path_ref()` или перед `build_project_context_snapshot()`:
`build_local_search_resource_manifest(project_root, available_knowledge_resources, workplace_manifest_path)`.

В `build_project_context_snapshot()` вызвать helper после `available_knowledge_resources` и добавить top-level `local_search_resources` в возвращаемый dict. Записи должны быть metadata-first: `id`, `resource_id`, `package_id`, `kind`, `path_ref`, `load_policy`, `index_policy`, `status/resolution_status`; без `path`, `resolved_path`, `local_path`, `content_roots` с приватными absolute paths.

2. Runtime/private search resolution

- Текущий search core строит roots только из фактических путей: `src/processforge_core/local_resource_search.py:86-114`.
- `mcp_server` сейчас загружает публичный snapshot и сразу передаёт его в `search()`: `tools/pf_runtime/mcp_server.py:82-91`.

Минимальная вставка: в `tools/pf_runtime/mcp_server.py:88-91` перед вызовом `search()` собрать неперсистентный runtime snapshot: взять metadata-first `local_search_resources`, приватно раскрыть `path_ref` через core helper, добавить transient `search_roots/content_roots` только в памяти, затем передать в `search()`. Это сохраняет публичный snapshot чистым.

3. FTS5 lifecycle

- Сейчас `build_index()` возвращает только `empty` или `current`: `src/processforge_core/local_resource_search.py:148-169`.
- `search()` при mismatch checksum молча rebuild-ит индекс и снова отдаёт `current`: `src/processforge_core/local_resource_search.py:172-188`.
- Ошибки SQLite/FTS5 не нормализованы в стабильный `unavailable`: `src/processforge_core/local_resource_search.py:155-198`.

Минимальная вставка: расширить lifecycle в `search()`/`build_index()`:
- `current`: индекс есть и checksum совпал.
- `empty`: индекс успешно построен, но документов нет.
- `stale`: индекс был найден, checksum отличался; rebuild выполнен или инициирован.
- `unavailable`: SQLite/FTS5/build/read failure, с безопасным `LocalSearchError("search_unavailable")` или структурным payload без traceback.

4. Ledger-bound stdio MCP smoke

- MCP handshake/tools/list уже реализованы: `tools/pf_runtime/mcp_server.py:119-129`.
- Session/project binding для non-session tools уже проверяется: `tools/pf_runtime/mcp_server.py:51-71`.
- Stable error wrapper уже возвращает код без диагностики: `tools/pf_runtime/mcp_server.py:112-136`.
- Session read layer также проверяет mismatch: `tools/pf_runtime/session_read.py:43-69`.
- Текущий smoke покрывает только FTS core: `tools/smoke_project_init_local_search_mcp.py:15-35`.

Минимальная вставка: расширить `tools/smoke_project_init_local_search_mcp.py` отдельными функциями:
- `smoke_search_current_empty_stale_unavailable()`
- `smoke_mcp_stdio_handshake_tools_list()`
- `smoke_mcp_session_project_mismatch()`

## Minimal reproducible fixture plan

1. Snapshot producer fixture

Создать temp project/workplace, ресурс с `path_ref`, один файл с уникальным токеном и один forbidden файл вне ресурса. Построить snapshot через `build_project_context_snapshot()`. Assert:
- top-level `local_search_resources` существует;
- каждая запись содержит `path_ref`;
- ни одна запись не содержит absolute `path`, `resolved_path`, `local_path`;
- forbidden файл не индексируется.

2. FTS lifecycle fixture

В temp project:
- `empty`: snapshot с разрешённым пустым каталогом, search возвращает `search_status == "empty"`;
- `current`: добавить `.md` с токеном, search возвращает `current` и результат;
- `stale`: построить индекс snapshot `s1`, затем вызвать search со snapshot `s2`; assert observable stale/rebuild status и новый checksum;
- `unavailable`: monkeypatch `sqlite3.connect` или FTS5 table creation на `OperationalError`; assert stable `search_unavailable`/`unavailable`, без traceback и без corrupt temp index.

3. MCP stdio fixture

Запустить `tools/pf_runtime/mcp_server.py --workplace <temp-workplace> --session <ledger-session>` как subprocess и передать JSON-RPC lines:
- `initialize` -> assert `serverInfo.name == "processforge"`;
- `notifications/initialized` -> no response;
- `tools/list` -> assert есть `pf.search`, `pf.project_initialization.status`, session tools;
- `tools/call` с bound session и conflicting `project_root` -> assert `isError == true` и text JSON содержит `error.code == "session_project_mismatch"`.

## Acceptance gate

Перед release acceptance требуется обновить smoke так, чтобы один запуск доказывал: snapshot producer не раскрывает приватные paths, FTS5 lifecycle различает `empty/current/stale/unavailable`, stdio MCP проходит initialize/tools-list и стабильно отклоняет Ledger mismatch.