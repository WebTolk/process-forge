# F0102 Assurance Report

## Verdict

**PASS with documented limits.** The bounded F01/F02 implementation is supported by independent source review and primary-run regression evidence. This is not release-readiness approval.

## Changes reviewed

- `src/processforge_core/garage.py`
  - Search now queries a project-scoped `ResourceSearchIndex`, preserving authorization across totals, pagination, results, and resolve operations.
- `src/processforge_core/core_update.py`
  - Added lexical collision checks for files, directories, symlinks, dangling symlinks, and non-directory ancestors.
  - Exact removed, owned, regular file ancestors may be replaced; user-owned or modified paths remain blocked.
  - `force_local_modifications` does not override unowned-path blockers.
- Regression coverage:
  - `tools/smoke_garage_cross_project_security.py`
  - `tools/smoke_garage_no_hooks_sessionless.py`
  - `tools/smoke_core_update_manifest.py`
  - `tools/garage_search_smoke_support.py`

Git-history origin reviewed: baseline commit `1aecc18b6824204ca45ab30241b92d26e6d583a5`; related search narrowing originated at `1e9c03d`.

## Evidence

Primary isolated public-copy validation:

- Corrected core-update smoke: **PASS**, exit 0.
- Corrected cross-project security smoke: **PASS**, exit 0.
- Baseline core-update smoke: **FAIL as expected**; baseline left an unowned `user-note.txt` collision unblocked.
- Baseline security smoke: **FAIL as expected**; baseline returned unauthorized shared results with `total=4`.

Primary genuine unmodified runs:

- `smoke_core_update_manifest.py`: **PASS**, exit 0.
- `smoke_garage_cross_project_security.py`: **PASS**, exit 0.
- `smoke_garage_no_hooks_sessionless.py`: **PASS**, exit 0.
- `smoke_project_resource_narrowing_search.py`: **PASS**, exit 0.

The core-update smoke covers:

- clean owned-ancestor replacement;
- modified owned-ancestor refusal and forced replacement with backup preservation;
- file, same-byte file, directory, and non-directory ancestor collisions;
- late-created user files;
- refusal with and without force;
- backup and no-mutation assertions;
- malicious traversal paths;
- workplace migration and failure recovery paths.

## Limits and residual risks

- Valid and dangling symlink cases were skipped because the Windows environment lacked symlink privileges (`WinError 1314`).
- Worker-local smoke execution was not repeated because the documented worker sandbox causes `TemporaryDirectory` failures (`WinError 5`). Primary execution outside that sandbox is the accepted evidence.
- The full release suite was not treated as complete; release readiness remains with the primary orchestration flow.
- No product files were modified by assurance.