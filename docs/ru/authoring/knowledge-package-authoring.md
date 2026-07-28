# Создание пакета знаний

Knowledge package собирает документацию, заметки, ссылки, фрагменты и индекс
ресурсов, которые агент может использовать при работе над проектами.

Пакет состоит из версионируемого манифеста и необязательных локальных папок:

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

Ресурсы могут жить вне package. Ссылайтесь на них через `path_ref` и реестры
workplace.

`registries/package-roots.yaml` определяет место чтения и записи для packages.
Команды Resource Management пишут в выбранный package root, а не в жёстко
заданный каталог `<workplace-root>/packages`. Используйте `--package-root <id>`,
если у workplace больше одного writable package root или если package
существует в нескольких roots.

## CLI

```bash
python bin/pf.py knowledge-package-create --workplace ./workplace --id docs.example-domain --title "Example Domain Documentation" --package-root global --apply
python bin/pf.py knowledge-package-doctor --workplace ./workplace --package docs.example-domain --package-root global
```

## Правила

- Используйте `path_ref`, а не public private paths.
- Записывайте selected package root как `package_root`.
- Тяжёлые ресурсы используют `load_policy: on_demand`.
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

Если author передаёт absolute path, Resource Management должен сопоставить его с
known root или зарегистрировать в private workplace registry до записи public
package/snapshot records.

Локальные ресурсы, принадлежащие package, должны использовать package-root
`path_ref` в generated indexes:

```yaml
path_ref:
  registry: package_roots
  id: global
  relative_path: docs.example-domain/resources/rules.md
```

## Правила package

- Knowledge package ids должны ясно обозначать subject matter или provider.
- Base technology knowledge представляется как knowledge packages плюс
  capabilities, а не как platform contracts.
- Private local documentation и деревья исходного кода используют workplace
  knowledge roots.
- API packages используют provider-specific ids вроде
  `docs.api.example-provider`; не создавайте один generic `docs.api` package.
