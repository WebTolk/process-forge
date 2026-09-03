# Derived Report Lifecycle Report

Date: 2026-08-24
Status: pass_with_conditions

## Finding

Several project-init reports are generated from a snapshot but do not currently
carry a durable lifecycle marker. Rewriting all historical report formats in
this slice would be high risk.

## Implemented Minimum

The final stabilization will expose a `derived_reports` section in
`pf.context`. It marks known generated reports as:

- `current` when present and not older than the current snapshot generation;
- `stale` when present but older than the current snapshot generation;
- `missing` when absent.

This gives agents an explicit current/stale signal without requiring them to
infer lifecycle by reading every report.

## Condition

Future report producers should write explicit snapshot id/checksum metadata into
each generated artifact. This slice provides the agent-facing stale marker, not
a full migration of all legacy report files.
