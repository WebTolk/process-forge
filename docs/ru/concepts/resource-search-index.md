# Индекс поиска ресурсов

Локальный поиск ProcessForge разделяет три границы:

- версионируемые ресурсы workplace объявляют, что можно индексировать;
- workplace-level SQLite FTS5 index хранит производные документы ресурсов;
- project context snapshot разрешает, какие `resource_id` доступны сессии.

Проекты не владеют поисковыми документами. Они хранят только разрешенные
идентификаторы ресурсов и fingerprints в snapshot. Приватная производная DB
находится здесь:

```text
<workplace>/runtime/search/local-resource-search.sqlite
```

`pf.search` является query adapter. Он не делает fallback на весь workplace,
другие проекты, home directory, Context7, web или скрытый `rg` по большим
деревьям исходного кода.

## Indexing Policy

Для ресурсов используется единый reusable contract:

```yaml
indexing:
  enabled: true
  mode: fulltext # fulltext | metadata | none
  fields:
    - title
    - description
    - tags
  sources:
    - path: articles
      mode: fulltext
      include:
        - "**/*.md"
      exclude:
        - drafts/**
    - path: core/6.1.2
      mode: metadata
      role: source_tree
```

`fulltext` кладет в FTS metadata и выбранные текстовые файлы. `metadata`
сохраняет только identity, title, description, version, root/path reference и
объявленную metadata. `none` исключает ресурс из локального поиска.

Большие source trees, SDK mirrors, vendor trees и multi-version platform
snapshots должны использовать `metadata`, если manifest явно не выбирает
маленький fulltext source. Поиск может вернуть navigation root, но для деталей
исходного кода Codex должен использовать обычные filesystem reads и `rg` внутри
выбранного root.

## SQLite Model

Производная DB ориентирована на ресурсы:

```text
resources
documents
documents_fts
index_state
```

`resources` хранит `resource_id`, `resource_type`, `version`, `fingerprint`,
`indexing_policy_hash`, `root_ref` и refresh status. `documents` хранит
`resource_id`, `relative_path`, `kind`, `title`, hashes и JSON metadata.
`documents_fts` хранит searchable fulltext fields. `index_state` хранит
authorization state текущего project snapshot без дублирования documents под
каждый проект.

## CLI

```bash
python bin/pf.py search-index status --project-root <project> --workplace <workplace>
python bin/pf.py search-index refresh --project-root <project> --workplace <workplace>
python bin/pf.py search-index rebuild --project-root <project> --workplace <workplace>
python bin/pf.py search-index doctor --project-root <project> --workplace <workplace>
python bin/pf.py search-index tick --project-root <project> --workplace <workplace>
```

`status` работает read-only. `status --verify-files` выполняет явную
fingerprint reconciliation и сообщает stale state, если содержимое разрешенного
ресурса изменилось. `refresh` обновляет indexable resources для текущего свежего
snapshot. `rebuild` удаляет производную DB и строит ее заново. `tick` является
bounded maintenance unit для оператора и Runtime scheduling.

## Runtime И MCP

Runtime maintenance должен периодически запускать `tick` для известных проектов
со свежими snapshots. PF-owned resource mutations помечают существующий index
state как stale; внешние изменения файлов обнаруживаются fingerprint-проверкой
во время `tick`.

`pf.search` никогда не выдает stale data как `fresh`. Если индекс missing, stale
или degraded, результат возвращает этот `search_status` и пустые matches до
maintenance refresh производной DB.

`pf.session_context` показывает компактную готовность поиска:

```yaml
search:
  status: fresh
  generation: <index-generation>
  stale: false
```

Resolved local paths являются request-local runtime data. Public snapshots и
artifacts хранят `path_ref`, а не private absolute paths.
