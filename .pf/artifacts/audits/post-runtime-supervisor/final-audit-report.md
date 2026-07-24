# Post Runtime Supervisor Audit Report

Status: completed with confirmed findings.

## Critical Findings

1. High: `environment.inherit: false` is ignored by `worker-run start`.
   - Evidence: `tools/processforge.py` starts from `os.environ.copy()` and then updates driver variables.
   - Repro: temp no-inherit driver with `PF_LEAK_TEST=should-not-leak`; worker stdout contained `should-not-leak`.
   - Impact: driver isolation contract is false; secrets and unrelated environment can leak into worker processes.

2. High: stale release archive can still pass archive validation.
   - Evidence: both `dist/processforge-v1.0.0.zip` and `dist/processforge.zip` exist; the older archive has fewer files.
   - Impact: `release-archive-test` proves internal archive consistency, not freshness against the current checkout.

3. High: Russian documentation is mojibake-corrupted.
   - Evidence: existing `README.ru.md`, `QUICKSTART.ru.md`, and `docs/ru/**` include mojibake markers such as `Рџ`, `РЎ`, and `вЂ`.
   - Impact: Russian documentation is not reliably readable.

## Major Findings

4. Medium: `generic-shell` validates but fails to start without `--executable`.
   - Evidence: `runtime-driver validate --driver generic-shell` returns PASS; `worker-run start` fails with empty argv.
   - Impact: registry validation reports a driver ready even when it requires runtime input.

5. Medium: supervisor returns success when worker start fails.
   - Evidence: temp plan with `generic-shell` produced `FAIL: empty command argv for bad-worker`, but supervisor exit code was `0`.
   - Impact: automation can treat failed scheduling as successful.

6. Medium: runtime driver validation does not enforce schema-level limits types.
   - Evidence: a driver with `limits.timeout_seconds: abc` passes `runtime-driver validate`.
   - Impact: later lifecycle commands can crash with uncaught conversion errors.

7. Medium: `process-supervisor` has incomplete artifact metadata.
   - Evidence: stages produce `process-record`, `worker-logs`, and `exit-record`, but `artifact_definitions` omits them.
   - Impact: process authoring/parity metadata is incomplete.

8. Medium: `process-supervisor` references missing artifact templates.
   - Evidence: `template: agent-run-state` and `template: worker-process-command` have no matching template files.
   - Impact: process definition points to non-existing authoring assets.

9. Medium: release note contradicts current supervisor MVP.
   - Evidence: `docs/releases/initial-release.md` still states no supervisor while current docs and process definitions describe a bounded supervisor MVP.

10. Medium: authoring parity WARNs are release-green.
    - Evidence: parity summaries report WARN while release-test passes.
    - Impact: release gate semantics are unclear for "To Fix Before Public Release" parity warnings.

## Minor Findings

11. Low: `release-test` is mutating and can mask generated-state issues by cleaning `.pf/runtime` before validation.

12. Low: Russian README is stale compared with English README for runtime driver/supervisor commands and documentation links.

## Passing Checks

- `python bin\pf.py release-test --root .` returned PASS.
- `python tools\validate-process-forge-checksums.py --root . --check` returned PASS.
- Schema validation and public cleanliness passed during release-test.

## Recommended Fix Order

1. Fix runtime safety: environment inheritance, limit type validation, `generic-shell` required executable semantics, and supervisor non-zero failure propagation.
2. Fix process metadata: missing artifact definitions and missing templates or template references.
3. Fix release freshness: remove or regenerate stale versioned archives and make archive validation detect stale artifacts.
4. Fix docs: stale release note, Russian README parity, and broader mojibake cleanup.
5. Decide release policy for authoring parity WARNs before public release.
