# Package Roots Authoritative Review

## Findings

No blocking issues found in the implemented package root flow.

## Coverage

- Positive smoke coverage confirms `knowledge-add-url` and `knowledge-add-resource` write under the configured `global` package root instead of the legacy `workplace/packages` fallback.
- Negative smoke coverage confirms unknown root ids fail and selected missing package roots fail in apply mode.
- Duplicate package ids across roots warn in doctor and fail writes without `--package-root`.
- Package manifests and indexes record `package_root: global`.
- Resource records generated from absolute known roots use public `path_ref` entries and do not retain resolved local paths.

## Residual Risks

- Resource availability is still registry-id/path-ref based; external URLs and remote resources are not healthchecked.
- The fallback `<workplace-root>/packages` path is intentionally retained for missing or empty registries, so users should keep `registries/package-roots.yaml` populated for deterministic writes.
- Duplicate handling is package-id based and does not compare package versions or content hashes.

## Verification

- `python -m py_compile tools/processforge.py tools/smoke_resource_management.py`: PASS
- `python tools/validate-process-forge-schemas.py --root .`: PASS
- `python tools/validate-public-cleanliness.py --root .`: PASS
- `python tools/validate-process-forge-checksums.py --root . --check`: PASS
- `python tools/processforge.py doctor-workplace --root .pf/runtime/smoke/package-roots-authoritative/workplace`: PASS with optional MCP WARN
- `python tools/processforge.py knowledge-package-doctor --workplace .pf/runtime/smoke/package-roots-authoritative/workplace --package test-package`: PASS
- `python tools/processforge.py doctor-project --project-root .`: PASS with existing project-init artifact WARN items
- `python tools/smoke_resource_management.py`: PASS
- `git diff --check`: PASS with CRLF normalization warnings only
