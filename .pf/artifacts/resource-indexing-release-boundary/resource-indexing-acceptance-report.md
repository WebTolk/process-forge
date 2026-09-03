# Resource Indexing Acceptance Report

## Matrix

- Knowledge A articles: `fulltext`, found by text query.
- Knowledge A source tree: `metadata`, found by title/version metadata only.
- Knowledge B: `fulltext`, found by text query.
- Knowledge C: indexed in workplace but not present in project snapshot, not visible to project query.
- Template T: README `fulltext`, files root `metadata`; boilerplate file content is not searchable.
- Tool X: metadata description is searchable.
- Versioned source tree: alternate snapshot selects version-specific source tree metadata.
- External content change: fingerprint check marks stale; tick refreshes; new content becomes searchable.

## Command

```text
python tools/smoke_resource_indexing_policy_acceptance.py
```

## Result

PASS.
