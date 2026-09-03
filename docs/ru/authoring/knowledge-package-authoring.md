# Создание пакета знаний

Knowledge package состоит из версионируемого manifest и необязательных
локальных папок:

```text
<package-root>/
|-- package.yaml
|-- README.md
|-- resources/
|-- indexes/
|-- prompts/
|-- summaries/
|-- tests/
|-- artifacts/
|-- reviews/
`-- handoffs/
```

Ресурсы могут находиться вне package. Ссылайтесь на них через `path_ref` и
workplace registries.

`registries/package-roots.yaml` является authoritative источником места чтения и
записи package. Команды Resource Management пишут в выбранный package root, а не
в жестко заданный `<workplace-root>/packages`. Используйте `--package-root <id>`,
если в workplace больше одного writable package root или если package существует
в нескольких roots.

## CLI

```bash
python bin/pf.py knowledge-package-create --workplace ./workplace --id docs.example-domain --title "Example Domain Documentation" --package-root global --apply
python bin/pf.py knowledge-package-doctor --workplace ./workplace --package docs.example-domain --package-root global
```

## Правила

- Используйте `path_ref`, а не public private paths.
- Записывайте selected package root как `package_root`.
- Тяжелые ресурсы используют `load_policy: on_demand`.
- Каждый searchable resource объявляет `indexing`; не полагайтесь на эвристики
  расширений файлов.
- На каждом resource фиксируйте license, source и update policy.
- После manifest changes обновляйте `indexes/resource-index.yaml`.
- Перед использованием package из project snapshot запускайте
  `knowledge-package-doctor`. Missing selected package roots fail; optional
  missing resources warn.

## Пути

Если resource хранится под workplace root, ссылайтесь через `path_ref`:

```yaml
path_ref:
  registry: knowledge_roots
  id: local-docs
  relative_path: official
```

Если author передает absolute path, Resource Management должен сопоставить его с
known root или зарегистрировать в private workplace registry до записи public
package/snapshot records.

Package-owned local resources должны использовать package-root `path_ref` в
generated indexes:

```yaml
path_ref:
  registry: package_roots
  id: global
  relative_path: docs.example-domain/resources/rules.md
```

## Indexing

Используйте `indexing.mode`, чтобы явно указать, что попадает в локальный поиск:

```yaml
resources:
  - id: joomla-articles
    kind: article_collection
    title: Joomla Articles
    load_policy: when_relevant
    path_ref:
      registry: knowledge_roots
      id: joomla-toolkit
      relative_path: articles
    indexing:
      enabled: true
      mode: fulltext
      fields: [title, description, tags]
      sources:
        - path: .
          mode: fulltext
          include: ["**/*.md"]
  - id: joomla-core-6.1.2
    kind: source_tree
    title: Joomla Core 6.1.2
    load_policy: on_demand
    path_ref:
      registry: knowledge_roots
      id: joomla-core
      relative_path: 6.x/6.1.2
    indexing:
      enabled: true
      mode: metadata
      fields: [title, description, version, path]
      sources:
        - path: .
          mode: metadata
          role: source_tree
```

`fulltext` подходит для подготовленных статей, заметок, README и коротких
reference documents. `metadata` используйте для source trees, vendor mirrors,
SDK snapshots и template file roots. `none` исключает ресурс из поиска.

## Правила package

- Knowledge package ids должны ясно обозначать subject matter или provider.
- Базовые технологические знания представлены как knowledge packages плюс
  capabilities, а не как platform contracts.
- Private local documentation и source trees используют workplace knowledge roots.
- API packages используют provider-specific ids вроде
  `docs.api.example-provider`; не создавайте один generic `docs.api` package.
- Update-able knowledge packages и resources объявляют `update_sites`; updates
  должны держать private absolute paths и heavy local mirrors вне public package
  metadata.
