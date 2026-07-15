# Knowledge Package Authoring

A knowledge package is a versioned manifest plus optional local folders:

```text
<package-root>/
├── package.yaml
├── README.md
├── resources/
├── indexes/
├── notes/
├── snippets/
├── examples/
└── templates/
```

Resources may live outside the package. Reference them through `path_ref` and workplace registries.

`registries/package-roots.yaml` is authoritative for package read/write
location. Resource Management commands write under the selected package root,
not under a hardcoded `<workplace-root>/packages` directory. Use
`--package-root <id>` when a workplace has more than one writable package root
or when updating a package that exists in duplicate roots.

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
  id: joomla-docs
  relative_path: official
```

If an author supplies an absolute path, Resource Management should map it to a known root or register it in the private workplace registry before writing public package/snapshot records.

Package-owned local resources should use a package-root `path_ref` in generated
indexes:

```yaml
path_ref:
  registry: package_roots
  id: global
  relative_path: platform.joomla/resources/rules.md
```
