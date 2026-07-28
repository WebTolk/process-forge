# Process Directory Layout Split Report

Status: complete

## Summary

ProcessForge moved from a flat process source layout to a root-aware catalog:

- `processes/core/` contains built-in ProcessForge process definitions.
- `processes/user/` is the default write target for process authoring.
- `processes/custom/` is reserved for imported, migrated, or brownfield-normalized process definitions.

`process_id` remains the stable identity. File paths are storage locations resolved through the central process resolver.

## Files Moved

- Moved 30 confirmed built-in process YAML files from `processes/*.yaml` to `processes/core/*.yaml`.
- Added `processes/user/.gitkeep`.
- Added `processes/custom/.gitkeep`.

## Pre-Release Cleanup

Removed `process-template-install` from the public catalog because it was an old lightweight install process with no matching CLI command and strong overlap with `process-authoring` / `process-create`.

Retained `knowledge-resource-add`, `template-add`, `tool-register`, `mcp-register`, and `platform-contract-install` because they still map to active resource-authoring or brownfield-normalization workflows.

## Resolver Changes

The central resolver now scans multiple roots and returns process metadata:

- `origin`
- `root`
- `path`
- `catalog_role`
- warnings for legacy flat paths and duplicate process ids

Search precedence is deterministic: user/custom roots before core, with legacy flat roots last.

## Process List Changes

`process-list` now prints columns for `origin`, `role`, `root`, and `path`, and supports filters:

- `--origin`
- `--role`
- `--status`
- `--all`

## Process Authoring Changes

`process-create` and `process-authoring-apply` now write process YAML to `processes/user/` by default.

Writing to `processes/core/` requires explicit `--core`.

## Release Boundary

Release policy includes `processes/core/**` and allows only `.gitkeep` placeholders under `processes/user/` and `processes/custom/`.

Real user/custom process definitions are treated as private project or workplace state and are forbidden in public release archives.

## Tests Added

- `tools/smoke_process_directory_layout.py`
- `tools/smoke_process_resolver_multiple_roots.py`
- `tools/smoke_process_list_origin_filters.py`
- `tools/smoke_process_authoring_writes_user_root.py`
- `tools/smoke_legacy_flat_process_layout_warning.py`
- `tools/smoke_release_pack_excludes_user_processes.py`
- `tools/smoke_process_id_stable_after_move.py`
- `tools/smoke_process_root_collision_policy.py`

## User Scenarios

The layout supports:

- Greenfield first workspace: start from core and author local processes into `user`.
- Studio workstation provisioning: install known packages and use PF core without recreating process definitions.
- Brownfield normalization: import or formalize existing snippets, docs, AGENTS.md content, and skills into `custom` or `user`.

## Current Verification

Passed:

- `python -m py_compile tools/processforge.py bin/pf.py`
- new process layout smokes
- existing built-in process catalog and completeness smokes
- process authoring materialization parity
- process definition schema contract smoke
- selected process/evolve/lifecycle smokes
- `python tools/validate-process-forge-schemas.py --root .`
- `python tools/validate-public-cleanliness.py --root .`

Final verification passed:

- `python tools/validate-process-forge-checksums.py --root . --check`
- `python bin/pf.py release-test --root . --public --fail-fast --timeout-scale 1`
- `python bin/pf.py release-test --root . --public --timeout-scale 1`
- `python bin/pf.py release-pack --root . --output dist/processforge.zip`
- `python bin/pf.py release-archive-test --archive dist/processforge.zip --root . --extracted-test full --timeout-scale 1`
- `git diff --check`

Archive result:

- `dist/processforge.zip`
- `dist/processforge.manifest.json`
- 677 public files
