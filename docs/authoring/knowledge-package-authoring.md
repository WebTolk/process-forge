# Knowledge Package Authoring

A knowledge package is a versioned manifest plus optional local folders:

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

Resources may live outside the package. Reference them through `path_ref` and workplace registries.

`registries/package-roots.yaml` is authoritative for package read/write
location. Resource Management commands write under the selected package root,
not under a hardcoded `<workplace-root>/packages` directory. Use
`--package-root <id>` when a workplace has more than one writable package root
or when updating a package that exists in duplicate roots.

## CLI

Create the package with the canonical Python launcher:

```bash
python bin/pf.py knowledge-package-create --workplace ./workplace --id docs.example-domain --title "Example Domain Documentation" --package-root global --apply
python bin/pf.py knowledge-package-doctor --workplace ./workplace --package docs.example-domain --package-root global
```

## Rules

- Use `path_ref`, not public private paths.
- Record the selected package root as `package_root`.
- Heavy resources use `load_policy: on_demand`.
- Keep license, source, and update policy on each resource.
- Refresh `indexes/resource-index.yaml` after manifest changes.
- Run `knowledge-package-doctor` before relying on the package from a project snapshot. Missing selected package roots fail; optional missing resources warn.

## Paths

If a resource is stored under a workplace root, reference it through `path_ref`:

```yaml
path_ref:
  registry: knowledge_roots
  id: local-docs
  relative_path: official
```

If an author supplies an absolute path, Resource Management should map it to a known root or register it in the private workplace registry before writing public package/snapshot records.

Package-owned local resources should use a package-root `path_ref` in generated
indexes:

```yaml
path_ref:
  registry: package_roots
  id: global
  relative_path: docs.example-domain/resources/rules.md
```

## Package Rules

- Knowledge package ids should identify the subject matter or provider clearly.
- Base technology knowledge is represented as knowledge packages plus
  capabilities, not as platform contracts.
- Private local documentation and source trees use workplace knowledge roots.
- API packages use provider-specific ids such as `docs.api.example-provider`;
  do not create one generic `docs.api` package.
- Update-able knowledge packages and resources declare `update_sites`; updates
  must keep private absolute paths and heavy local mirrors out of public package
  metadata.
