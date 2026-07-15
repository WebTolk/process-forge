# Resource Privacy

Public project files must not expose private absolute paths.

Use `path_ref` instead:

```yaml
path_ref:
  registry: private_resource_paths
  id: joomla-docs
path_status: private_absolute_path_redacted
```

External resources also use `path_ref`:

```yaml
path_ref:
  registry: external_resources
  id: mdn-html-docs
  url: "https://developer.mozilla.org/"
```

Workplace registries may contain local paths because they are private machine configuration. Project snapshots include resource indexes and policy metadata, not raw private paths.

## Absolute Resource Paths

Resource Management must not discard absolute paths supplied by the user. It should:

- resolve the path through `path_constants`;
- check whether the path is under an existing `knowledge_roots`, `template_roots`, or `package_roots` entry;
- write a `path_ref` to the matching root when possible;
- otherwise store the private absolute path in the workplace private registry and expose only `path_ref` in public package/snapshot records.
