# Индекс поиска ресурсов

ProcessForge разделяет три слоя:

- project context snapshot задаёт границу авторизации;
- SQLite search index является приватным, производным и пересобираемым;
- MCP только адаптирует запросы.

Индекс хранится в runtime рабочей области:

```text
<workplace>/runtime/search/local-resource-search.sqlite
```

В одном индексе могут быть разные snapshot-scopes, но каждый `pf.search` фильтруется через Ledger session, привязанный project и свежий project snapshot. Скрытого fallback на весь workplace, другие проекты, home directory, Context7 или web быть не должно.

## CLI

Оператор может диагностировать и обслуживать индекс без MCP:

```bash
python bin/pf.py search-index status --project-root <project> --workplace <workplace>
python bin/pf.py search-index refresh --project-root <project> --workplace <workplace>
python bin/pf.py search-index rebuild --project-root <project> --workplace <workplace>
python bin/pf.py search-index doctor --project-root <project> --workplace <workplace>
python bin/pf.py search-index tick --project-root <project> --workplace <workplace>
```

`status` работает read-only. `refresh` обновляет scope текущего project snapshot. `rebuild` удаляет производную DB и строит её заново для текущего project snapshot scope.

`status --verify-files` выполняет явную fingerprint-проверку файлов текущего snapshot scope. Так можно пометить индекс `stale`, если разрешённые файлы изменились вне ProcessForge.

`tick` — один bounded maintenance pass для Runtime или оператора. По умолчанию он проверяет fingerprints и делает refresh только если scope отсутствует или stale. MCP-запросы не выполняют такую проверку на каждый query.

## Автоматические maintenance triggers

ProcessForge запускает тот же bounded maintenance pass из lifecycle-команд, которые могут изменить авторизованный поисковый scope:

- `workplace-init` создаёт приватный runtime-отчёт поиска и делает tick для уже известных onboarded projects под workplace.
- `project-onboard`, `project-init-repair` и `project-context-refresh` делают tick текущего проекта после записи свежего project context snapshot.
- resource-authoring команды `knowledge-add-url`, `knowledge-add-resource`, `knowledge-index-refresh`, `template-create`, `tool-register`, `mcp-register`, `platform-create` и `platform-contract-install` делают tick известных onboarded projects под workplace.
- `update-apply` и `update-rollback` сначала помечают затронутые project snapshots как stale, затем запускают maintenance; stale projects пропускаются до `project-context-refresh`.

Автоматический pass пишет приватный производный отчёт:

```text
<workplace>/runtime/search/latest-maintenance.yaml
```

Он намеренно ограничен известными ProcessForge projects и никогда не строит глобальный workplace index. Если project context устарел, ProcessForge выводит `SEARCH_INDEX_SKIPPED` с нужным следующим действием вместо rebuild по устаревшим authorization data.

## Runtime и MCP

`pf.search` возвращает навигационные результаты, а не генерирует ответ. В payload есть:

- `search_status`
- `index_generation`
- `total`
- `limit`
- `offset`
- `items` / `results`

`pf.session_context` возвращает компактную готовность поиска:

```yaml
search:
  status: fresh
  generation: <index-generation>
  stale: false
```

Индекс может хранить приватные resolved paths как runtime data. Public snapshots и public artifacts должны хранить `path_ref`, а не machine-local absolute paths.

## Текущие ограничения

Этот slice сохраняет индекс производным и пересобираемым, использует SQLite FTS5 и не добавляет скрытый глобальный поиск. Lifecycle-triggered maintenance покрывает first-run, project context refresh, resource authoring и update apply/rollback paths. Crash recovery states beyond safe rebuild и production-scale benchmark coverage остаются будущими slices.
