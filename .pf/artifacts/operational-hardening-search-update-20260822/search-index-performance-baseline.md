# Search Index Performance Baseline

Run: `operational-hardening-search-update-20260822`

## Measured Scope

Baseline used the isolated smoke fixture in `tools/smoke_search_update_operational_hardening.py`.

Covered operations:

- initial refresh;
- fingerprint stale check after file change;
- refresh after change;
- refresh after add;
- refresh after delete;
- dirty event mark + refresh;
- schema mismatch rebuild;
- concurrent read loop during maintenance.

## Result

The full operational smoke completed under the normal CLI smoke timeout and returned:

```text
PASS: search/update operational hardening smoke
```

## Policy Consequence

Use `tick` as the bounded operational unit. It is safe for operator/Runtime scheduling because it performs no work when the scope is already fresh and rebuilds only derived DB state.

## Limit

This is not a production corpus benchmark. A later benchmark should measure large local documentation roots before hardcoding daemon cadence.
