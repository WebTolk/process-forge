# F02 update worker log

## 2026-09-10T05:09:48Z — worker-f02-update

- Scope: corrective attempt for bounded unowned Core archive path collisions.
- Files changed: `src/processforge_core/core_update.py` retained the first-attempt lexical collision preflight; `tools/smoke_core_update_manifest.py` was repaired for public portability and stronger no-mutation coverage. Added private evidence helper/raw outputs under this directory and private scratch runner under `.pf/tmp/.../f02-update/`.
- Decisions: public smoke uses standard `tempfile.TemporaryDirectory` calls and contains no Git, `.pf`, baseline, or private-temp coupling. Private baseline proof is pinned to `1aecc18b6824204ca45ab30241b92d26e6d583a5` and loads it only in the private helper.
- Checks: `py_compile` exit 0; `git diff --check` exit 0; public smoke exit 0 with explicit Windows symlink and broken-symlink skips; isolated public-only copy (no `.git`/`.pf`) exit 0; baseline/private comparison exit 0 and shows pre-fix overwrite versus repaired block.
- Residual risks: Windows symlink privilege was unavailable (`WinError 1314`), so both symlink cases were recorded as skips; primary should run privileged symlink coverage where supported. Normal system TemporaryDirectory invocation is blocked by this worker sandbox, so the passing smoke runs used a private invocation-only fixed-temp shim without altering public tests.
