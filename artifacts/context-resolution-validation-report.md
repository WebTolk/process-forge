# Context Resolution Validation Report

## Scope

ProcessForge session bootstrap and context resolution MVP.

## Commands

- `python -m py_compile tools/processforge.py tools/validate-process-forge-schemas.py tools/validate-public-cleanliness.py tools/validate-process-forge-checksums.py`
- `python tools/processforge.py --help`
- `python tools/processforge.py context-resolve --project-root .`
- `python tools/processforge.py session-start --mode resume --project-root .`
- `python tools/processforge.py context-compile --project-root . --assignment assignments/processforge-session-bootstrap-implementation.md --capsule`
- `python tools/processforge.py doctor-context --project-root . --assignment assignments/processforge-session-bootstrap-implementation.md`
- Negative temp-project smoke: unknown required capability blocks context resolution and prevents ECP compile.
- `python tools/validate-process-forge-schemas.py`
- `python tools/validate-public-cleanliness.py`
- `python tools/validate-process-forge-checksums.py --write`
- `python tools/validate-process-forge-checksums.py`

## Results

- `py_compile` exited 0.
- `processforge.py --help` exposes `session-start`, `context-resolve`, `context-compile`, and `doctor-context`.
- `context-resolve` wrote context index, resolved rules, conflict report, and runtime cache with status `warn`.
- `session-start --mode resume --project-root .` printed a report and did not write files.
- `session-start --mode resume --project-root . --allow-write` wrote `artifacts/session-status-report.md`.
- `context-compile` wrote `contexts/processforge-session-bootstrap-implementation.ecp.yaml` and `contexts/processforge-session-bootstrap-implementation.capsule.yaml`.
- `doctor-context` passed for the project root and assignment ECP freshness.
- Negative temp-project smoke passed: blocked context prevented ECP compilation.
- Final schema validation, public cleanliness, checksum read-only validation, CLI help, doctor-context, and `git diff --check` passed.

## Notes

- `context-resolve` currently returns `warn` for optional unresolved capabilities; this is expected for the MVP and does not block ECP compilation.
- `git diff --check` reported only LF-to-CRLF working-copy warnings from Git.

## Expected Smoke Coverage

- CLI exposes `session-start`, `context-resolve`, `context-compile`, and `doctor-context`.
- Report-only resume prints status without writing `artifacts/session-status-report.md`.
- Context resolve creates context index, resolved rules, conflict report, and private runtime cache.
- Context compile creates assignment ECP and capsule when conflicts are not blocked.
- Doctor context validates current context and assignment ECP freshness.

## Residual Risks

- Semantic merge validation remains intentionally lightweight in the MVP.
- Optional missing capabilities may produce warnings while keeping context usable.
