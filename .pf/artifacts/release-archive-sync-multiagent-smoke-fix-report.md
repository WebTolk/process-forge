# Release Archive Sync And Multiagent Smoke Fix Report

Date: 2026-07-20 21:48 +04:00
Agent: Codex

## Scope

The task reconciled the release archive with the current ProcessForge source,
removed stale generated artifacts, fixed the multiagent assignment smoke so its
exact-overlap expectation is independent of filesystem case sensitivity, and
revalidated the 1.0.0 release surface.

## What Was Stale

- `dist/processforge-v0.1.0.zip` and
  `dist/processforge-v0.1.0.manifest.json` were still tracked under `dist/`
  even though the canonical release is now `1.0.0`.
- The release docs still showed generic `dist/processforge-release.zip`
  commands instead of the current canonical
  `dist/processforge-v1.0.0.zip` artifact.
- The multiagent smoke used `Tools/ProcessForge.py` versus
  `tools/processforge.py` for an exact overlap assertion. That depends on
  filesystem case behavior and is not a portable exact-overlap fixture.
- The current archive CLI surface had `update sources`, but the acceptance
  surface required `update sources-list --validate`.

## Archive Sync

`python bin/pf.py release-pack --root . --output dist/processforge-v1.0.0.zip`
rebuilt the canonical release archive and manifest.

Final inspection:

- source release-surface file count: `384`
- release archive file count: `384`
- release manifest file count: `384`
- zip and manifest file lists match: `true`
- missing expected update files: none
- forbidden archive entries: none
- extra stale files: none
- manifest version: `1.0.0`

The rebuilt archive contains the required update framework files:

- update schemas under `schemas/*update*.schema.json`
- update registry/runtime templates under `templates/registries/` and
  `templates/runtime/update/`
- `tools/smoke_multiagent_assignment_contract.py`
- `tools/smoke_update_framework_readonly.py`
- `tools/smoke_update_framework_validation.py`

The archived `tools/processforge.py` contains the required update commands:

- `update bootstrap-source list`
- `update bootstrap-source validate`
- `update sources-list --validate`
- `update entity-sources rebuild`
- `update entity-sources list`
- `update manifest validate`

## Smoke Fix

`tools/smoke_multiagent_assignment_contract.py` now uses the same normalized
path value, `tools/processforge.py`, for both the existing writer ownership and
the incoming assignment. The smoke still fails on true write-scope overlap, but
the fixture no longer relies on `Tools/ProcessForge.py` and
`tools/processforge.py` collapsing on case-insensitive filesystems.

The assignment/capsule contract semantics were preserved by keeping the smoke
coverage for write scope ownership, glob overlap, shared read context,
forbidden-file precedence, and normalized contract outputs.

## Cleanup

`python bin/pf.py clean --root . --release` now removes the project-local
`.pf/runtime/` directory in addition to Python caches and generated cache
directories. This is deliberately narrower than removing every `runtime`
directory, so release fixtures such as `templates/runtime/update/` remain
packaged.

Removed stale dist artifacts:

- `dist/processforge-v0.1.0.zip`
- `dist/processforge-v0.1.0.manifest.json`

Generic `dist/processforge-release.*` artifacts were not present in the final
`dist/` directory.

## Version And Boundary Checks

Version consistency:

- `VERSION`: `1.0.0`
- `.pf/process-forge.yaml`: `process_forge.version: 1.0.0`
- release archive: `dist/processforge-v1.0.0.zip`
- release manifest: `dist/processforge-v1.0.0.manifest.json`
- manifest version: `1.0.0`

Platform-agnostic boundary:

- A targeted grep over release-facing core files outside `docs/**`,
  `examples/**`, and policies found no forbidden platform/domain markers.
- `python tools/validate-public-cleanliness.py --root .` passed.

## Checks

Passed:

- `python -m py_compile tools/processforge.py tools/smoke_update_framework_readonly.py tools/smoke_multiagent_assignment_contract.py bin/pf.py`
- `python tools/smoke_multiagent_assignment_contract.py`
- `python tools/smoke_update_framework_readonly.py`
- `python tools/smoke_update_framework_validation.py`
- `python tools/smoke_manifest_driven_platforms.py`
- `python tools/smoke_platform_inheritance.py`
- `python tools/validate-process-forge-schemas.py --root .`
- `python tools/validate-public-cleanliness.py --root .`
- `python tools/validate-process-forge-checksums.py --root . --check`
- `python bin/pf.py release-test --root .`
- `python bin/pf.py release-pack --root . --output dist/processforge-v1.0.0.zip`
- `python bin/pf.py release-archive-test --archive dist/processforge-v1.0.0.zip`
- archive inspection script from the task, extended with counts and CLI command checks
- `git diff --check`

## Remaining Limitations

- POSIX was not executed in this Windows workspace. The exact-overlap fixture is
  now platform-independent by construction because both sides use the identical
  normalized path value.
- `doctor-project` passes after cleanup with warnings about optional onboarding
  skeleton artifacts missing, including `.pf/runtime/bin/pf.py`; `release-test`
  treats this as acceptable and passed.
