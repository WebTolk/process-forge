# Runtime Supervisor Audit Fix Report

- run: `runtime-supervisor-audit-fix-shell-agents`
- timestamp: `2026-07-24T16:33:08+04:00`
- status: `implemented`
- built-in subagents used for this fix: `no`

## Fixed

- `environment.inherit: false` now starts workers with an isolated environment.
- `generic-shell` is no longer start-ready without an explicit executable.
- Invalid runtime limits fail validation before worker start.
- Supervisor tick/run now returns non-zero when a worker cannot be started.
- Failed/timed-out worker runs are not collectible as successful task output.
- `process-supervisor` now defines `process-record`, `worker-logs`, and `exit-record`.
- Missing runtime templates were added.
- Canonical public archive is `dist/processforge.zip`.
- Stale versioned dist archive artifacts were removed.
- Public release gates now check stale dist artifacts, Russian mojibake markers, and public-release parity WARN tags.

## Validation

- `python bin/pf.py release-test --root . --public`: PASS
- `python bin/pf.py release-pack --root . --output dist/processforge.zip`: PASS, 455 files
- `python bin/pf.py release-archive-test --archive dist/processforge.zip --root .`: PASS
- `python tools/processforge.py process-doctor --project-root . --process process-supervisor`: PASS
- `python tools/validate-process-forge-checksums.py --root . --check`: PASS
- `git diff --check`: PASS
