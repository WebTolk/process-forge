# Release-Test Reliability Fix Report

## Scope

This slice fixes P1 reliability risks in the v0.1 release-test path. It does not implement Process Authoring MVP, daemon/watchers, runner/supervisor, orchestrator, webhook send, GUI, marketplace, remote sync, or publishing.

## Why Release-Test Could Hang Or Misreport

- `bin/pf.py` used `subprocess.call`, leaving a wrapper process around the real CLI.
- Generated `.pf/runtime/bin/pf.py` used the same wrapper pattern.
- `smoke_first_run.py` and `smoke_resource_management.py` launched subprocesses without timeout.
- `release-test` did not print every command before launching it.
- Windows `os.execv` preserved stdout but did not preserve argv quoting or child exit codes in this environment.

## Launcher Changes

- `bin/pf.py` no longer uses `subprocess.call`.
- POSIX launch uses `os.execv`.
- Windows launch uses explicit `os.spawnv(os.P_WAIT, ...)` fallback because `os.execv` split arguments with spaces and returned false success exit codes here.
- Windows argv is quoted with `subprocess.list2cmdline([arg])` before exec/spawn.
- The project-local launcher template generated for `.pf/runtime/bin/pf.py` uses the same approach.
- Broken distribution paths still emit explicit `FAIL` diagnostics and exit non-zero.

## Smoke Timeout Changes

- `tools/smoke_first_run.py` now wraps subprocess calls with timeout, output capture, command/cwd/timeout diagnostics, and stdout tail.
- `tools/smoke_resource_management.py` now wraps subprocess calls with timeout and clear failure diagnostics.
- `tools/smoke_resource_authoring_processes.py` already had timeout isolation and was reverified after launcher changes.

## Release-Test Changes

- `release-test` prints `RUN <label>:` and the command before every subprocess and flushes stdout.
- Every release-test subprocess has a per-command timeout.
- Timeout output returns FAIL with `timeout after Ns` and captured output tail.
- `py_compile` now includes both `tools/processforge.py` and `bin/pf.py`.

## Archive Verification

Added:

```bash
python tools/processforge.py release-archive-test --archive dist/processforge-v0.1.0.zip
```

It checks:

- archive exists;
- manifest exists;
- forbidden archive entries are absent;
- manifest file list matches ZIP entries;
- extracted archive runs `release-test`.

Release pack now includes the minimal public `.pf` skeleton and `.gitignore` needed for extracted-archive `release-test`:

- `.pf/AGENTS.md`
- `.pf/process-forge.yaml`
- `.pf/hooks.yaml`
- `.pf/artifacts/checksum-inventory.sha256`
- `.gitignore`
- `.processforge-releaseignore`

## Checks Passed

- `python -m py_compile tools/processforge.py`
- `python -m py_compile bin/pf.py`
- `python tools/validate-process-forge-schemas.py --root .`
- `python tools/validate-public-cleanliness.py --root .`
- `python tools/validate-process-forge-checksums.py --root . --check`
- `python tools/smoke_first_run.py`
- `python tools/smoke_resource_management.py`
- `python tools/smoke_resource_authoring_processes.py`
- `python tools/processforge.py release-check --root .`
- `python tools/processforge.py release-test --root .`
- `python tools/processforge.py release-pack --root . --output dist/processforge-v0.1.0.zip`
- `python tools/processforge.py release-archive-test --archive dist/processforge-v0.1.0.zip`

## Remaining Limitations

- Windows uses a documented spawn fallback because `os.execv` did not preserve argv/exit behavior in this environment.
- `doctor-project --project-root .` still reports known non-blocking WARN entries for this repository's self-contained dogfooding mode.
- Process Authoring MVP remains the next pre-public-release step.
