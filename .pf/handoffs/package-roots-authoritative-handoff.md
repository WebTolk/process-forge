# Package Roots Authoritative Handoff

## Current State

Package roots are now authoritative for Resource Management package reads and writes.

Use `--package-root <id>` when the target package root must be explicit or when the same package id exists in multiple package roots.

## Commands Updated

- `knowledge-add-url`
- `knowledge-add-resource`
- `knowledge-index-refresh`
- `knowledge-package-doctor`
- `doctor-workplace`

## Important Behaviors

- `registries/package-roots.yaml` missing or empty: fallback to `<workplace-root>/packages` with WARN.
- Unknown package root id: FAIL.
- Selected package root with missing path: dry-run WARN, apply FAIL.
- Duplicate package id across roots: doctor WARN, write without `--package-root` FAIL.
- Public snapshot/resource records: keep `path_ref` and package root ids only.

## Follow-Up

- If future commands write package manifests, route them through `resolve_package_root` and `resolve_package_path`.
- If package version arbitration is introduced, extend duplicate detection beyond package id.
- Keep package root absolute paths in workplace-private registries, not public project snapshots.
