# Core Boundary Scan Guards Report

- task: `processforge_core_boundary_scan_guards_pf_agent_master_prompt.md`
- status: implemented

## Path Role Model

ProcessForge now has explicit project path roles for `project_root`,
`project_pf_root`, `distribution_root`, `workplace_root`, `knowledge_root`,
`runtime_root`, and `package_cache`.

The default scan policy excludes `distribution_root`, `workplace_root`,
`knowledge_root`, `runtime_root`, and `package_cache` from project source
inventory.

## Scan Guards Implemented

- Added role-aware `collect_project_source_inventory`.
- Added default `scan_policy` with role exclusions and default path excludes.
- Added PF core exception rules: PF-looking roots require
  `processforge-development` or `processforge-core-development`.
- Updated `.pf/process-forge.yaml` to declare `project.type:
  processforge-development`.

## Doctor Warnings And Errors

- `doctor-project` now fails when a PF-looking root is used as a generic
  project.
- `doctor-project` warns when project root contains distribution/workplace
  subtrees protected by scan guards.
- `doctor-project` warns when knowledge roots live inside project root.
- `doctor-workplace` now reports missing `knowledge_roots.local-docs` as
  missing or empty, and reports configured local-docs as PASS.

## Project-Local Package Index

Project-local package resources under `.pf/packages` no longer produce a false
missing resource-index warning when the index is optional. Real missing indexes
for non-project-local packages now include the expected path and fix command.

## Platform Snapshot Semantics

Project snapshots now distinguish:

- `available_platform_contracts`
- `selected_platform_contracts`
- `platform_stack`
- `platform_selection`

Meta-project types can have available contracts with
`platform_selection.status: not_applicable` and an empty selected stack.

## platform-create Include Levels

`platform-create` now supports required, recommended, and optional include
levels for packages, templates, tools, and MCP providers. Legacy ambiguous
arguments are kept as optional aliases and documented as deprecated in help.

## Process Layout Stale Refs

New smokes check active public/project-facing refs for `processes/core`,
`processes/user`, and `processes/custom` layout, and reject refs to removed
`process-template-install`.

## Windows UTF-8 Docs

Installation docs now document PowerShell UTF-8 console setup:

```powershell
chcp 65001
$OutputEncoding = [System.Text.UTF8Encoding]::new()
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new()
[Console]::InputEncoding = [System.Text.UTF8Encoding]::new()
```

## Release-Test Trace Diagnostics

`release-test --trace-smokes` writes
`.pf/runtime/release-test/latest-trace.ndjson` with smoke label, elapsed time,
timeout budget, and timeout reason.

## Tests Run

Passed so far:

- `python tools/smoke_project_scan_excludes_distribution_root.py`
- `python tools/smoke_project_scan_excludes_workplace_root.py`
- `python tools/smoke_project_scan_excludes_knowledge_roots.py`
- `python tools/smoke_processforge_core_project_requires_explicit_type.py`
- `python tools/smoke_project_local_package_index_detection.py`
- `python tools/smoke_agent_workspace_platform_availability_snapshot.py`
- `python tools/smoke_platform_create_include_levels.py`
- `python tools/smoke_release_test_trace_timeout_reporting.py`
- `python tools/smoke_windows_utf8_docs.py`
- `python tools/smoke_pf_project_process_refs_follow_layout.py`
- `python tools/smoke_no_removed_process_refs.py`

Final verification:

- `python tools/validate-process-forge-schemas.py --root .`: PASS
- `python tools/validate-public-cleanliness.py --root .`: PASS
- `python tools/validate-process-forge-checksums.py --root . --check`: PASS
- Existing process/layout/context/catalog smokes requested by the assignment:
  PASS
- `python bin/pf.py release-test --root . --only smoke_project_scan_excludes_distribution_root --public --fail-fast --timeout-scale 1`:
  PASS
- `python bin/pf.py release-test --root . --only smoke_project_local_package_index_detection --public --fail-fast --timeout-scale 1`:
  PASS
- `python bin/pf.py release-test --root . --public --fail-fast --timeout-scale 1 --trace-smokes`:
  PASS, elapsed 342.40s
- `python bin/pf.py release-test --root . --public --timeout-scale 1 --trace-smokes`:
  PASS, elapsed 360.08s
- `python bin/pf.py release-pack --root . --output dist/processforge.zip`:
  PASS, 692 files
- `python bin/pf.py release-archive-test --archive dist/processforge.zip --root . --extracted-test full --timeout-scale 1`:
  PASS, nested release-test elapsed 339.93s
- `git diff --check`: PASS with LF-to-CRLF working-copy warnings only

## Remaining Limitations

- Role-aware inventory is currently a core helper used by doctors/smokes; there
  is no separate end-user inventory CLI yet.
- Explicit include of knowledge roots as project source remains future policy.
- `release-test --trace-smokes` records trace after each check completes or
  times out; it is not a streaming trace viewer.
