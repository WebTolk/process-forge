# Path Constants / Resource Paths Review

## Reviewed Object

ProcessForge path constants and resource path resolver implementation.

## Reviewer

ProcessForge implementation reviewer

## Result

pass_with_conditions

## Findings

- PASS: `workplace.yaml` supports `path_constants` and init-workplace writes defaults.
- PASS: Registries can use `${PF_*}` paths and doctor-workplace resolves them.
- PASS: Absolute paths are accepted in workplace/private registries without being copied into public project snapshots.
- PASS: `knowledge-add-resource` maps absolute paths under known roots to `path_ref` and stores unmatched private paths in the workplace private registry on apply.
- PASS: `doctor-project` keeps failing public snapshots that contain local absolute paths.
- PASS: Smoke tests cover positive and negative path cases.
- WARN: Tool and MCP healthcheck commands are resolved as strings but not executed by a runner.
- WARN: Optional missing root paths are warnings, not blockers, unless the registry entry is available or requires existence.

## Evidence

- `tools/processforge.py`
- `tools/smoke_resource_management.py`
- `schemas/path-constants.schema.json`
- `schemas/path-ref.schema.json`
- `docs/concepts/path-constants.md`
- `docs/concepts/path-resolution.md`

## Recommendation

Use path constants for workplace-local base roots and keep project `.pf/` snapshots limited to `path_ref` records.
