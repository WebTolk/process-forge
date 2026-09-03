# Spark review: project-init-local-search-mcp-20260821

## Итог
Обнаружены воспроизводимые несоответствия с контрактом; статус проверки — **requires rework**.

- **[High] Неполный контрактный payload статуса `project-init-status`**  
  `project_initialization.status` возвращает только часть `resources` и упрощённые состояния `workplace/mcp`. В контракте (`.pf/artifacts/.../project-initialization-contract.md:35-39`) требуется `workplace` с 4 состояниями, `resources` как агрегаты по required/recommended/activated/missing для knowledge/tools/mcp/templates и отдельные уровни `mcp` до `verified`.  
  Реализация сейчас: `workplace` = `"reachable"` при любом заданном значении, либо `"auto"`; `resources` = `knowledge` и `templates` только счётчики; `mcp` = только `"active_in_snapshot"`/`"not_configured"`.  
  См. [project_initialization.py](D:\Dev\process-forge\src\processforge_core\project_initialization.py:37).

- **[High] `workplace` в статусе всегда помечается как доступный при передаче пути**  
  Реестрный путь не проверяется в `project_initialization.status`; недействительный `--workplace` помечается как `reachable` вместо `missing|unreachable`.  
  См. [project_initialization.py](D:\Dev\process-forge\src\processforge_core\project_initialization.py:37) и вызов в [processforge.py](D:\Dev\process-forge\tools\processforge.py:5844).

- **[Medium] `local_resource_search` не выдаёт все контрактные состояния `search_status`**  
  `search_status` возвращает только `empty|current`, отсутствуют `stale|unavailable`, хотя контракт ожидает их как часть жизненного цикла индекса (`project-initialization-contract.md:102-107`). Также нет явного учета дрейфа по fingerprint-достоверности/маркеру stale в самом кэше поиска, только перестройка по контрольной сумме снапшота.  
  См. [local_resource_search.py](D:\Dev\process-forge\src\processforge_core\local_resource_search.py:169,186,188).

- **[Medium] Неоднозначная обработка авторизации по `project_root` в MCP non-session tools**  
  Для `pf.project_state/pf.project_initialization.status/pf.resolve/pf.search/pf.workplace_state` при конфликте `project_root` выбрасывается `PermissionError`, а `safe_tool_error` мапит его в общий `read_failed`. Это теряет контрактный стабильный код ошибки для mismatch-сценариев.  
  См. [mcp_server.py](D:\Dev\process-forge\tools\pf_runtime\mcp_server.py:68-71,112-116).

- **[Info] Недостаточно доказательной smoke-проверки MCP-видимости**  
  Существующий smoke-пакет покрывает только FTS5 search (`smoke_project_init_local_search_mcp.py`) и не проверяет stdio MCP handshake/tools-list/tools-call/session-mismatch, хотя это явно выделено как ожидаемая проверка.  
  См. [implementation-report](D:\Dev\process-forge\.pf\artifacts\project-init-local-search-mcp-20260821\cli-integration-implementation-report.md:16-21) и контракт `[project-initialization-contract.md](D:\Dev\process-forge\.pf\artifacts\project-init-local-search-mcp-20260821\project-initialization-contract.md:19)`.

## Приложение
С учётом назначения (review-only, no code changes) правки не применялись.