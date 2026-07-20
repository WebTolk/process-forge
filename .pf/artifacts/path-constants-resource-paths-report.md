# Path Constants / Resource Paths Report

## Status

implemented

## Implemented

- Added `workplace.yaml:path_constants` support with defaults for `PF_WORKPLACE`, `PF_DISTRIBUTION`, `PF_KNOWLEDGE`, `PF_TEMPLATES`, `PF_TOOLS`, `PF_MCP`, `PF_PLATFORM_CONTRACTS`, `PF_PROCESS_TEMPLATES`, `PF_RUNTIME`, and `PF_CACHE`.
- Added a shared path resolver in `tools/processforge.py` for `${CONST}`, absolute Windows-style paths, absolute POSIX-style paths, and relative paths.
- Added `path-resolve` CLI for inspecting expansion and resolution.
- Updated registry resolution so workplace registries may use constants in registry paths and root entries.
- Updated Resource Management normalization so absolute resource paths are mapped to known roots when possible, otherwise registered through a private workplace registry in apply mode.
- Kept public package/snapshot records on `path_ref` plus `path_status`; resolved private paths are not written to public snapshots.
- Extended `doctor-workplace`, `doctor-project`, and `knowledge-package-doctor` checks around constants, registry paths, path_ref, and public snapshot absolute-path leaks.
- Added path schemas, templates, documentation, and smoke/negative tests.

## Supported Path Forms

- `${PF_KNOWLEDGE}/example/docs`
- Windows-style absolute paths in workplace/private files
- POSIX-style absolute paths in workplace/private files
- `../relative/path`
- `relative/path`

## Public Snapshot Protection

Project snapshots continue to expose ids, `path_ref`, `load_policy`, and metadata. `doctor-project` fails when public snapshot YAML or Markdown contains local absolute paths.

## Absolute Resource Paths

When a resource file contains an absolute path, Resource Management:

1. resolves constants and normalizes separators;
2. checks known workplace roots;
3. writes a `path_ref` to the matching root when possible;
4. registers an unmatched private path in the workplace private registry during `--apply`;
5. writes only `path_ref` into package/index/snapshot records.

## Validation

- `python -m py_compile tools/processforge.py tools/smoke_resource_management.py`: PASS
- `python tools/validate-process-forge-schemas.py --root .`: PASS
- `python tools/validate-public-cleanliness.py --root .`: PASS
- `python tools/validate-process-forge-checksums.py --root . --check`: PASS
- `python tools/processforge.py events-validate --project-root .`: PASS
- `python tools/processforge.py doctor-project --project-root .`: PASS with existing bootstrap WARN items for missing project-init artifacts.
- `python tools/smoke_resource_management.py`: PASS
- `git diff --check`: PASS with Git CRLF normalization warnings only.

Smoke tests cover constant resolution, Windows/POSIX absolute paths in workplace registries, public snapshot leak failure, known-root `path_ref` mapping, unknown constants, and invalid `path_ref` registry ids.

## Remaining Limits

- No full VFS or package manager was added.
- Existence checks are warnings for optional/missing local roots unless an entry is marked available or explicitly requires existence.
- Healthcheck command execution remains future runner work.
