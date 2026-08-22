# Resource Index Performance Report

## Fixture Benchmark

Command:

```text
python tools/smoke_resource_indexing_policy_acceptance.py
```

Result: PASS.

The fixture creates metadata-only source trees with many PHP files and verifies exactly one `documents` row for the metadata source tree resource. PHP file content is not inserted into FTS.

## Joomla Corpus Benchmark

Attempted root:

```text
D:\.agents\docs\Joomla-core
```

Observed result:

```json
{
  "joomla_root_exists": false,
  "resources": 0,
  "documents": 0,
  "fts_rows": 0,
  "db_size_bytes": 61440,
  "full_rebuild_seconds": 0.0357,
  "query_p50_ms": 0.948,
  "query_p95_ms": 1.934
}
```

The configured Joomla core snapshot root is absent in this environment. This blocks a real production-size Joomla core benchmark here, but the acceptance fixture confirms the required invariant: FTS row count does not grow with source-tree PHP file count when policy is `metadata`.
