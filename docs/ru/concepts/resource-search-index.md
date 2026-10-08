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
состояние каталога Workplace и области снапшотов проектов в общей DB. Снапшоты
определяют разрешённые идентификаторы ресурсов для каждого поискового запроса;
документы не дублируются для каждого проекта.

## CLI

```bash
python bin/pf.py search-index status --project-root <project> --workplace <workplace>
python bin/pf.py search-index refresh --project-root <project> --workplace <workplace>
python bin/pf.py search-index rebuild --project-root <project> --workplace <workplace>
python bin/pf.py search-index doctor --project-root <project> --workplace <workplace>
python bin/pf.py search-index tick --project-root <project> --workplace <workplace>
```

Все команды требуют корень проекта и читают его контекстный снапшот. `status`
работает без изменения индекса; `status --verify-files` проверяет отпечатки
разрешённых файлов и сообщает состояние `stale`, если их содержимое изменилось.
`refresh` индексирует ресурсы, разрешённые снапшотом, соблюдая `indexing.mode`.
`rebuild` удаляет производную DB и строит её заново; `tick` выполняет один
ограниченный проход для области снапшота проекта.

`refresh`, `rebuild` и `tick` требуют состояния контекста `fresh` или
`fresh_with_updates`; иначе они отказывают с кодом выхода 1. `status` и `doctor`
доступны и при других состояниях контекста. `doctor` показывает свежесть
контекста проекта как `PASS` для этих двух состояний и как `WARN` для остальных.

## Runtime И MCP

Планировщик Runtime использует существующую операцию Core `maintenance_tick`
для каталога Workplace отдельно от CLI-команд с областью проекта. Эта операция
Core не обходит проекты и не требует запущенного Runtime, Ledger или активных
сессий. Изменения ресурсов средствами PF помечают существующее состояние
индекса как `stale`; внешние изменения файлов обнаруживаются проверкой
отпечатков при обслуживании.

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
