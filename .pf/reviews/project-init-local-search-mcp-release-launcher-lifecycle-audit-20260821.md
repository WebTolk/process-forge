# Release Launcher Lifecycle Audit

## Scope

Assignment: `project-init-local-search-mcp-release-launcher-lifecycle-audit-20260821`

Read scope used:
- `tools/processforge.py`
- `.pf/process-forge.yaml`
- `.pf/process-forge.local.yaml`
- `.pf/.gitignore` was listed but does not exist.

No product code was edited.

## Reproduction Status

I did not run the destructive reproduction command because `python tools/processforge.py clean --root . --release` would remove `.pf/runtime/`, which is outside this read-only audit's allowed write scope.

I did run non-mutating documented command discovery:
- `python tools/processforge.py release-test --list`
- `python tools/processforge.py clean --help`
- `python tools/processforge.py doctor-project --help`
- `python tools/processforge.py release-check --help`

The command list confirms the lifecycle order: `release-test` runs `clean release artifacts` early and `doctor-project` near the end.

## Finding

`doctor-project` can require `.pf/runtime/bin/pf.py` after `release-test` has already removed `.pf/runtime/`.

Exact boundary:

- `project_runtime_launcher_files()` generates:
  - `.pf/runtime/bin/pf.py`
  - `.pf/runtime/bin/pf`
  - `.pf/runtime/bin/pf.bat`

Evidence: `tools/processforge.py:3733-3888`

- project onboarding writes those launcher files through `files.update(project_runtime_launcher_files(flow_root))`.

Evidence: `tools/processforge.py:5756`

- release cleanup treats the whole `.pf/runtime` directory as removable generated state.

Evidence:
- `safe_remove_generated_path()` removes `root/.pf/runtime`: `tools/processforge.py:6489-6491`
- `command_clean --release` walks the whole root and removes approved generated paths: `tools/processforge.py:6505-6518`

- `release-test` defaults to `clean_first=True`, inserts `clean release artifacts` near the start, and later runs `doctor-project`.

Evidence:
- `release_test_commands(... clean_first: bool = True ...)`: `tools/processforge.py:6629`
- `doctor-project` release command: `tools/processforge.py:6783`
- cleanup insertion: `tools/processforge.py:6785-6786`

- `doctor-project` explicitly fails missing `runtime/bin/pf.py` unless `auto_workplace_mode` is true.

Evidence: `tools/processforge.py:20287-20315`

This project has `.pf/process-forge.local.yaml`, so `auto_workplace_mode` is not enabled by the `workplace.reference: auto` value in `.pf/process-forge.yaml`; the local manifest branch is taken first.

Evidence:
- local manifest branch: `tools/processforge.py:20133-20142`
- auto mode only when local manifest is absent and public manifest says `workplace.reference: auto`: `tools/processforge.py:20152-20157`
- local file exists and points to a workplace manifest: `.pf/process-forge.local.yaml`

## Impact

The release-test lifecycle is internally inconsistent for a ProcessForge development checkout with local workplace coordinates:

1. onboarding creates `.pf/runtime/bin/pf.py`;
2. release cleanup removes `.pf/runtime/`;
3. doctor-project later still expects `.pf/runtime/bin/pf.py`;
4. the failure message says linked projects need the launcher because they do not contain ProcessForge core tools.

That rationale is correct for normal linked projects, but not for a ProcessForge distribution development checkout, which already contains `bin/pf.py` and `tools/processforge.py`.

## Recommended Smallest Safe Remediation

Change only the `doctor-project` missing-launcher check.

Keep `clean --release` deleting `.pf/runtime/`; it is private/generated runtime state and should not be preserved for release hygiene.

In `command_doctor_project`, when `rel_path == "runtime/bin/pf.py"` is missing, downgrade the result from `FAIL` to `WARN` for self-contained ProcessForge distribution development projects, for example when `project_type_allows_processforge_core(manifest_data)` is true or when `looks_like_processforge_distribution(project_root)` is true.

Preserve the existing `FAIL` for ordinary linked projects.

Suggested behavior:

- normal linked project without launcher: `FAIL`
- auto workplace mode: existing `WARN`
- ProcessForge core/development checkout containing core tools: `WARN`

This matches the existing diagnostic text: only projects that do not contain ProcessForge core tools need the project-local runtime launcher as a hard requirement.

## Follow-Up Verification

After the remediation, run the narrow lifecycle check:

```bash
python tools/processforge.py release-test --root . --only "clean release artifacts" --only "doctor-project"
```

Then run the broader release gate as appropriate:

```bash
python tools/processforge.py release-test --root .
```