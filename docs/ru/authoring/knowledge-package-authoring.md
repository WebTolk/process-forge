# Knowledge package authoring

Knowledge package собирает документацию, заметки, links, snippets и resource
index, которые агент может использовать при работе над проектами.

Пакет состоит из versioned manifest и optional local folders:

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

Resources могут жить вне package. Ссылайтесь на них через `path_ref` и
workplace registries.

`registries/package-roots.yaml` определяет read/write location для packages.
Resource Management commands пишут в выбранный package root, а не в hardcoded
`<workplace-root>/packages` directory. Используйте `--package-root <id>`, если
у workplace больше одного writable package root или если package существует в
нескольких roots.

## CLI

```bash
python bin/pf.py knowledge-package-create --workplace ./workplace --id docs.example-domain --title "Example Domain Documentation" --package-root global --apply
python bin/pf.py knowledge-package-doctor --workplace ./workplace --package docs.example-domain --package-root global
```

## Rules

- Используйте `path_ref`, а не public private paths.
- Записывайте selected package root как `package_root`.
- Heavy resources используют `load_policy: on_demand`.
- На каждом resource фиксируйте license, source и update policy.
- После manifest changes обновляйте `indexes/resource-index.yaml`.
- Перед использованием package из project snapshot запускайте
  `knowledge-package-doctor`. Missing selected package roots fail; optional
  missing resources warn.

## Paths

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

Package-owned local resources должны использовать package-root `path_ref` в
generated indexes:

```yaml
path_ref:
  registry: package_roots
  id: global
  relative_path: docs.example-domain/resources/rules.md
```

## Package rules

- Knowledge package ids должны ясно обозначать subject matter или provider.
- Base technology knowledge представляется как knowledge packages плюс
  capabilities, а не как platform contracts.
- Private local documentation и source trees используют workplace knowledge
  roots.
- API packages используют provider-specific ids вроде
  `docs.api.example-provider`; не создавайте один generic `docs.api` package.
