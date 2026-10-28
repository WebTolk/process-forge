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

Хранилище SQLite FTS5 принадлежит workplace и находится вне checkout проекта,
установленного Core и публичных knowledge/release packages. Оно может содержать
приватный текст документов. Общая физическая DB не даёт проекту или Work доступ
к чужим ресурсам: фильтры авторизации применяются до выдачи результатов,
количества совпадений и ранжирования.

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

Сохранённый fingerprint ресурса также учитывает полный набор разрешённых корней,
включая пустые fulltext-каталоги. Явная проверка и выборочное обновление метаданных
замечают смену корня без чтения текстов невыбранных ресурсов.

## CLI

Явная операция уровня workplace требует целевого workplace и `--apply`:

```bash
python bin/pf.py search-index-maintain --workplace <workplace> --apply --json
```

Она читает текущий зарегистрированный каталог workplace без обхода проектов.
Результат schema-version-1 имеет kind `pf.search_index.maintenance`, область
workplace, `project_count: 0`, `results` и относительную ссылку `report`.
Успех возвращает exit code 0, отказ или сбой — ненулевой код. Без `--apply`
команда отказывает до создания maintenance service. Контекст проекта и права
проектной Work не разрешают обслуживание всего workplace: вызывающему нужны
отдельные полномочия на эту область.

Существующие команды с областью проекта сохраняют свои параметры:

```bash
python bin/pf.py search-index status --project-root <project> --workplace <workplace>
python bin/pf.py search-index refresh --project-root <project> --workplace <workplace>
python bin/pf.py search-index rebuild --project-root <project> --workplace <workplace>
python bin/pf.py search-index doctor --project-root <project> --workplace <workplace>
python bin/pf.py search-index tick --project-root <project> --workplace <workplace>
```

Эти команды с областью проекта требуют его корень и читают контекстный снапшот. `status`
работает без изменения индекса; `status --verify-files` проверяет отпечатки
разрешённых файлов и сообщает состояние `stale`, если их содержимое изменилось.
`refresh` индексирует ресурсы, разрешённые снапшотом, соблюдая `indexing.mode`.
`rebuild` заменяет производный поисковый набор в одной SQL-транзакции,
сохраняя существующий файл DB и его store identity envelope; `tick` выполняет
один ограниченный проход для области снапшота проекта.

`refresh`, `rebuild` и `tick` требуют состояния контекста `fresh` или
`fresh_with_updates`; иначе они отказывают с кодом выхода 1. `status` и `doctor`
доступны и при других состояниях контекста. `doctor` показывает свежесть
контекста проекта как `PASS` для этих двух состояний и как `WARN` для остальных.
Три явные изменяющие команды делегируют общему maintenance owner через
`run_scoped`: они не загружают каталог всего workplace и не расширяют выборку
источников. Legacy `rebuild` сохраняет прежнюю замену общего производного набора:
очищает все поисковые строки и строит их из переданной выборки проекта,
а не обновляет только выбранные ресурсы.

## Пакетное добавление знаний

`knowledge-add-batch` принимает YAML с `schema_version: 1` и списком `resources`
в существующем формате записи `knowledge-add-resource`:

```yaml
schema_version: 1
resources:
  - id: example-guide
    kind: article
    title: Example guide
    description: A registered reference
    source:
      type: url
      url: https://example.org/guide
    license:
      name: unknown
```

```bash
python bin/pf.py knowledge-add-batch --workplace <workplace> --package <package> --batch-file batch.yaml --dry-run --json
python bin/pf.py knowledge-add-batch --workplace <workplace> --package <package> --batch-file batch.yaml --apply --json
```

Пакет должен существовать. По умолчанию и с `--dry-run` команда ничего не
записывает и не индексирует. Каждый элемент проходит существующую транзакцию
манифеста, индекса ресурсов и приватного реестра с аудитом и восстановлением.
После обычной ошибки элемента обработка продолжается; результаты сохраняют
порядок входного списка. В конце только успешные идентификаторы одним вызовом
передаются `WorkplaceIndexMaintenanceService.run_resources`. Компонент сужает
текущий зарегистрированный каталог, сохраняет остальные строки SQLite и не
читает тексты невыбранных документов. Загрузка содержимого URL не выполняется.
Ошибка добавления или индексации даёт ненулевой код выхода; сбой индексации
не отменяет уже завершённые добавления.

Выборочный проход подтверждает обработку выбранных ресурсов. Он снимает известные
уведомления, только если все они относятся к успешным идентификаторам, нет старого
сбоя и новых изменений во время прохода. Компонент обновляет метаданные каталога
по сохранённым строкам, только если совпадают все зарегистрированные ресурсы и
их политики, без чтения остальных текстов. Поэтому после чистого успешного пакета
поиск продолжает работать. Неизвестные и невыбранные изменения, неполное покрытие
и старые ошибки сохраняют недоступность общего поиска до соответствующего явного
обслуживания. Дата последней полной сверки не меняется. Будущая сверка по
расписанию использует тот же компонент; сам планировщик в alpha4 не реализован.

## Runtime И MCP

Физический каталог Workplace читает конкретный Core-класс
`WorkplaceSearchCatalogReader`. Он читает текущие реестры, зарегистрированные
корни пакетов, knowledge packages активных официальных пакетов и шаблоны, затем
разрешает ссылки на их пути. Каталог не зависит от project context, CLI, Runtime,
Ledger или сессии. Обслуживание индекса и ограниченная поисковая проекция сессии
обращаются к нему напрямую; исторические функции каталога в монолите делегируют
ему работу. Каталог не даёт проекту права искать по произвольным ресурсам:
авторизация и проверки свежести в проектных CLI/MCP сохраняются.

`WorkplaceIndexMaintenanceService` владеет явным выполнением индексации,
сериализацией, устойчивым состоянием и восстановлением, переиспользуя движок
`ResourceSearchIndex`. CLI уровня workplace вызывает `run`, существующие
refresh/rebuild/tick с областью проекта — `run_scoped`. Холодный
`IndexMaintenanceJob.execute()` вызывает тот же `run` при явном обращении.
Alpha4 не регистрирует в Runtime поисковую задачу, поток, цикл, таймер или
autostart. Периодический запуск относится к будущему планировщику PF и здесь
не реализован.

Инициализация, refresh, repair, чтение контекста и проектный поиск только
наблюдают существующий индекс. Они не строят его, не ставят обслуживание в
очередь и не ждут завершения. Регистрация ресурсов средствами PF и пути
update/rollback могут пометить существующее производное состояние dirty,
оставляя согласование явному обслуживанию. Наблюдение не проверяет тела
документов. Внешние изменения файлов обнаруживаются при явном
`status --verify-files`, проверяющем `tick` или обслуживании workplace.

Одновременно workplace обслуживает один явный writer. Конкурирующий writer
получает ограниченный по времени отказ busy. OS-lock освобождается при смерти
процесса; устойчивая запись `running` остаётся незавершённой до следующего
разрешённого прохода уровня workplace. Сбой или прерывание не объявляются
свежим индексом, а проход с областью проекта не снимает незавершённое состояние
всего workplace. Состояние и история находятся в
`runtime/search/maintenance-state.json` и `runtime/search/maintenance-history/`,
последний отчёт — в `runtime/search/latest-maintenance.yaml`. Это приватные
производные/операционные файлы, а не публичные knowledge artifacts.

`pf.search` не выдаёт известные устаревшие данные как `fresh`. Если индекс
missing, stale, building или degraded, результат возвращает этот `search_status` и пустые matches до
maintenance refresh производной DB.

Свежесть контекста, готовность обязательных ресурсов, физическая доступность
поиска и разрешённое покрытие наблюдаются отдельно. Готовый контекст может
не иметь индекса; свежий физический индекс может не содержать документов,
разрешённых конкретному проекту. `pf.work.search` сохраняет отдельный путь
проверенного материала с pinned/current/stage доступом и проверками материала.
Обслуживание workplace не расширяет этот доступ и не заменяет текущие проверки.

`pf.session_context` показывает компактную готовность поиска:

```yaml
search:
  status: fresh
  generation: <index-generation>
  stale: false
```

Resolved local paths являются request-local runtime data. Public snapshots и
artifacts хранят `path_ref`, а не private absolute paths.

## Граница backend и будущего хранения

SQLite FTS5 — единственный реализованный backend; он обеспечивает лексический
полнотекстовый поиск. Узкий `ResourceIndexBackend` описывает операции, которые
реально нужны обслуживанию: `mark_dirty`, `refresh`, `rebuild` и `maintenance_tick`. Он
отделяет выполнение поискового backend от общего прикладного компонента;
это не API соединений с DB, ORM или второй алгоритм индексации.

Общий [SQL API](database-api.md) уже предоставляет `Database`, `SqlSession`,
`SchemaManager` и именованные профили. Реализован только драйвер SQLite;
SQL репозиториев сохраняет его диалект. Query и observation напрямую используют
`ResourceSearchIndex`, а поиск материала Work — отдельный FTS5-индекс в памяти.
Замена maintenance factory не заменяет эти пути. Для будущего поискового адаптера
MySQL/MariaDB/PostgreSQL нужны отдельные conformance-тесты токенизации,
ранжирования, фильтров доступа, атомарности и восстановления: SQL-драйвер
сам по себе не обеспечивает эквивалентность. Векторный/гибридный поиск требует
явных chunking, модели/версии/размерности embeddings, identity поколения и
правил обновления/удаления. RAG — прикладной pipeline retrieve/augment/generate,
а не драйвер DB. Эти адаптеры, embeddings, RAG и общий планировщик остаются
будущими задачами; alpha4 их не предоставляет и не включает скрыто.
