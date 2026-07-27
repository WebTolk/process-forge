# Project Context Lock Model

`context_requirements` in `.pf/process-forge.yaml` are the project-level dependency declaration. They describe the knowledge packages, resources, templates, tools, and platform contracts the project wants, similar to package requirements.

`.pf/contexts/project-context.snapshot.yaml` is the resolved lock file. It records a generated snapshot id, checksumable content, resolved resource instances, generations, fingerprints, and reproducibility level. Older generations are kept under `.pf/contexts/project-context.snapshots/`.

## Resource Modes

- `multi_version`: pinned by version and instance id. A newer version reports `fresh_with_updates`; a missing pinned version is `broken`.
- `single_current`: only one current instance is supported. Fingerprint changes make the snapshot `stale`.
- `rolling_index`: current generation changes over time. Generation or fingerprint changes make the snapshot `stale`.
- `external_live`: reproducibility is best effort. Freshness depends on the last recorded external fingerprint or generation.

## Freshness

`project-context-check` reports one of:

- `fresh`: current snapshot still matches the declared requirements and resolved resources.
- `fresh_with_updates`: pinned resources are still available, but newer compatible versions exist.
- `stale`: refresh is needed because rolling or current resources changed, or an update marked the snapshot stale.
- `broken`: a pinned resource or required source is missing.

`context_policy` controls session-start behavior. The default is to continue on `fresh`, notify on `fresh_with_updates`, ask the operator on `stale`, and block on `broken`.

## Capsules

Assignment capsules pin the snapshot id and `sha256` checksum that existed when the capsule was created. Refreshing project context writes a new snapshot generation for future capsules and does not rewrite existing capsules.

