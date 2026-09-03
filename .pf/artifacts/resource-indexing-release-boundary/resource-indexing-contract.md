# Resource Indexing Contract

## Contract

```yaml
indexing:
  enabled: true
  mode: fulltext | metadata | none
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

## Semantics

- `fulltext`: index declared metadata and selected text source files.
- `metadata`: index resource identity, title, description, version, path/root reference, and declared metadata only.
- `none`: exclude the resource from local search.

## Resource Identity

Search documents are keyed by resource identity:

```text
resource_id
resource_version/fingerprint
document_relative_path
```

`snapshot.id` is not part of document identity. Snapshot data is used only for query authorization.

## Applicable Resource Types

- Knowledge/articles: usually `fulltext`.
- Source trees/Joomla core snapshots/vendor mirrors: `metadata`.
- Templates: README/description may be `fulltext`; files root is `metadata`.
- Tools/processes/platform contracts: metadata/fulltext over descriptive fields where exposed through a resource record.
