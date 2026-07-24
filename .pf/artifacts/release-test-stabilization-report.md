# Release Test Stabilization Report

## Scope

Implemented the release-test and shell-supervisor stabilization assignment from
`задания/processforge_release_test_stabilization_shell_subagent_master_prompt.md`.

## Changes

- Added release-test timing, flushing, selectable checks, fail-fast,
  timeout scaling, public-gate selection, and machine-readable reports under
  `.pf/runtime/release-test/`.
- Stabilized `release-archive-test` with freshness checks before extraction,
  extracted-test modes, timeout scaling, and full public extracted test by
  default.
- Converted update framework smokes to `tools/processforge_subprocess.py`.
- Reduced `smoke_resource_authoring_processes.py` hang risk with progress
  output and a lightweight PowerShell-file check.
- Added detached `worker-run start --detach` while preserving default wait mode.
- Reworked supervisor tick to observe running workers, start new workers
  detached, collect completed workers, enforce dependencies, enforce active
  write-scope overlap blocking, and propagate failed/timed-out workers.
- Added `tools/smoke_full_shell_agents_supervisor.py`.
- Updated public docs and examples for detached supervisor behavior and native
  subagent boundaries.

## Validation Evidence

- `python -u tools/smoke_full_shell_agents_supervisor.py` PASS.
- `python -u tools/smoke_process_supervisor.py` PASS.
- `python -u tools/smoke_process_supervisor_lifecycle.py` PASS.
- `python -u tools/smoke_process_supervisor_tick.py` PASS.
- `python -u tools/smoke_shell_launched_agents_supervisor_fix.py` PASS.
- `python -u tools/smoke_resource_authoring_processes.py` PASS.
- `python -u tools/smoke_update_framework_readonly.py` PASS.
- `python -u tools/smoke_update_framework_validation.py` PASS.
- `python tools/validate-process-forge-schemas.py --root .` PASS.
- `python tools/validate-public-cleanliness.py --root .` PASS.
- `python bin/pf.py release-test --root . --only py_compile --only public-gate --fail-fast --timeout-scale 1 --public` PASS.
- `python bin/pf.py release-test --root . --public --fail-fast --timeout-scale 1` PASS.

## Final Packaging Evidence

- `python tools/validate-process-forge-checksums.py --root . --check` PASS.
- `python bin/pf.py release-pack --root . --output dist\processforge.zip`
  PASS; wrote 456 files.
- `python bin/pf.py release-archive-test --archive dist\processforge.zip --root . --extracted-test full --timeout-scale 1` PASS.
- Extracted archive `release-test --public` PASS.
- `git diff --check` returned 0; Git printed CRLF normalization warnings on
  this Windows checkout.
