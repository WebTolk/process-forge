# Индекс поиска ресурсов

ProcessForge разделяет три слоя:

- snapshot проекта задаёт границу авторизации;
- SQLite search index является приватным, производным и пересобираемым;
- MCP только адаптирует запрос.

Индекс хранится в runtime рабочей области:

```text
<workplace>/runtime/search/local-resource-search.sqlite
```

В одном индексе могут быть разные snapshot-scopes, но каждый `pf.search` фильтруется через Ledger session, привязанный project и свежий project snapshot. Скрытого fallback на весь workplace, другие проекты, home directory, Context7 или web быть не должно.

## CLI

Оператор может диагностировать индекс без MCP:

```bash
python bin/pf.py search-index status --project-root <project> --workplace <workplace>
python bin/pf.py search-index refresh --project-root <project> --workplace <workplace>
python bin/pf.py search-index rebuild --project-root <project> --workplace <workplace>
python bin/pf.py search-index doctor --project-root <project> --workplace <workplace>
```

`status` работает read-only. `refresh` обновляет scope текущего snapshot проекта. `rebuild` удаляет производную DB и строит её заново для текущего snapshot проекта.

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

Текущий slice сохраняет индекс производным и пересобираемым, использует SQLite FTS5 и не добавляет скрытый глобальный поиск. Периодическое Runtime maintenance, инкрементальный dirty marking, расширенные crash recovery states и production benchmark остаются следующими slices.
