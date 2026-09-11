# Primary disposition of independent review

Date: 2026-09-11. Owner: primary orchestrator.

Both original Luna shell review reports remain unchanged and retain their
conditional verdicts. Primary accepted and resolved all four concrete findings:

| Finding | Resolution | Acceptance evidence |
| --- | --- | --- |
| Equal relative names in multiple authorized search roots collide | Canonical root digest participates in document identity, SQLite uniqueness and freshness. Derived schema is 6; public relative paths retained. | `validation/current/smoke_search_multiple_roots.{json,txt}`; original HEAD fails the regression. |
| Symlink resolution may raise RuntimeError | Root, source and discovered-path resolution handle both OSError and RuntimeError and isolate the affected resource. | Multiple-roots regression injects RuntimeError and verifies graceful isolation. |
| Expected-report fingerprint bypasses the safe resolver | Task doctor/fingerprint uses the common project-contained resolver before expected-report reads; invalid paths produce an invalid-output record. | `validation/current/smoke_expected_report_containment.{json,txt}`. The guarded task-doctor probe failed before repair; failure retained in `validation/current/history/`. |
| MCP schema validator ignores oneOf | Exactly one schema branch must accept the value; invalid evidence is rejected before dispatch, including notifications. | `validation/current/smoke_mcp_jsonrpc_validation.{json,txt}`; native stdio and dispatch-counter coverage. Pre-repair failure retained in history. |

Primary verdict: all four actionable findings resolved; focused regressions PASS.

Boundaries:

- Actual symlink creation is unavailable for the current Windows account. Real
  traversal/absolute-path and file-root probes ran, as did injected resolution
  failure. No real symlink fixture PASS is claimed.
- The updater concurrency note is unverified and pre-existing. A05 validates
  migration inputs, structured apply failures and incremental recovery evidence;
  independent concurrent updater transactions are not claimed to be serialized.
  See `review-followup-design.md`.
- Native Codex payloads have no documented stable occurrence ID. Lifecycle
  sources are distinguished, identical redelivery is idempotent, and no provider
  identity is invented for indistinguishable repeated same-source occurrences.
  Rejected audit hypothesis H01 was not implemented.
- Worker/reviewer sandbox temporary-directory failures are preserved. Primary
  ran behavioral tests outside that worker restriction; exit code alone was
  never treated as validation.

The full source-suite outcome is recorded separately at final assurance.
Archive, extracted-package, installed-Core and public-release qualification
are outside this source-remediation delivery.
