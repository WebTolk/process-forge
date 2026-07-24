# Runtime CLI Worker Audit

Source: delegated read-only worker `audit-runtime-cli-worker`.

Findings:

1. High: `environment.inherit: false` is ignored during worker start. `worker-run start` always starts from `os.environ.copy()`, so parent environment variables leak into a driver that explicitly disables inheritance.
2. Medium: `generic-shell` validates as PASS without an executable override, then fails at runtime with `FAIL: empty command argv`.
3. Medium: supervisor exits 0 even when a worker start fails.
4. Medium: runtime driver validation does not enforce schema-level `limits.timeout_seconds` integer type and can allow later uncaught `ValueError`.

Local verification:

- Confirmed env leak with `PF_LEAK_TEST=should-not-leak`; worker stdout contained `should-not-leak`.
- Confirmed `runtime-driver validate --driver generic-shell` returns PASS.
- Confirmed supervisor output includes `FAIL: empty command argv for bad-worker` while `SUPERVISOR_EXIT=0`.
- Confirmed a driver with `timeout_seconds: abc` passes runtime-driver validation.
