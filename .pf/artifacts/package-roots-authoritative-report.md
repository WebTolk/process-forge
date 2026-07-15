# Package Roots Authoritative Report

## Status

implemented

## Implemented

- Made `registries/package-roots.yaml` the authoritative package read/write registry for Resource Management package commands.
- Added `resolve_package_root` and `resolve_package_path` helpers with explicit handling for default roots, unknown root ids, missing root paths, writable flags, and fallback behavior.
- Added `--package-root <id>` to `knowledge-add-url`, `knowledge-add-resource`, `knowledge-index-refresh`, and `knowledge-package-doctor`.
- Updated package writes so package manifests and `indexes/resource-index.yaml` are written under the selected package root.
- Added duplicate package-id detection across package roots. Write commands fail without `--package-root`; doctor reports the duplicate as a warning.
- Updated resource index generation so package-local resources use `path_ref.registry: package_roots` and public records do not expose resolved root paths.
- Added package root doctor coverage to `doctor-workplace`.
- Added package events: `package.root.resolved`, `package.root.missing`, `package.root.unavailable`, `package.created`, `package.updated`, `package.index.updated`, `package.doctor.failed`, and `package.duplicate.detected`.
- Updated schemas, templates, docs, and Resource Management smoke tests.

## Runtime Policy

- Unknown `--package-root` ids fail.
- Selected missing package root paths warn in dry-run and fail in apply mode.
- Registry missing or empty falls back to `<workplace-root>/packages` with a warning.
- Public snapshots and public resource records keep root ids and `path_ref`, not absolute local paths.
- Heavy package resources remain index-only until explicitly requested through `load_policy`.

## Validation

- `python -m py_compile tools/processforge.py tools/smoke_resource_management.py`: PASS
- `python tools/validate-process-forge-schemas.py --root .`: PASS
- `python tools/validate-public-cleanliness.py --root .`: PASS
- `python tools/validate-process-forge-checksums.py --root . --check`: PASS
- `python tools/processforge.py doctor-workplace --root .pf/runtime/smoke/package-roots-authoritative/workplace`: PASS with optional MCP WARN
- `python tools/processforge.py knowledge-package-doctor --workplace .pf/runtime/smoke/package-roots-authoritative/workplace --package test-package`: PASS
- `python tools/processforge.py doctor-project --project-root .`: PASS with existing project-init artifact WARN items
- `python tools/smoke_resource_management.py`: PASS
- `git diff --check`: PASS with CRLF normalization warnings only

## Files

- `tools/processforge.py`
- `tools/smoke_resource_management.py`
- `schemas/package-manifest.schema.json`
- `schemas/package-roots-registry.schema.json`
- `templates/registries/package-roots.yaml`
- `templates/knowledge-package.yaml`
- `templates/knowledge-resource-index.yaml`
- `docs/concepts/path-resolution.md`
- `docs/concepts/knowledge-resources.md`
- `docs/concepts/linked-workplace-model.md`
- `docs/authoring/knowledge-package-authoring.md`
- `docs/authoring/workplace-configuration.md`
