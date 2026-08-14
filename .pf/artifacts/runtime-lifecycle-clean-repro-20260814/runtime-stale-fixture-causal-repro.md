# Stale Runtime metadata causal fixture

Result: PASS

The isolated fixture used the same material pattern as the current checkout: a `ready` service record, no `runtime.lock`, a dead PID, and an unreachable endpoint.

- Fixture classification: `stale` / `stale`
- Automatic restart result: `started`
- Session registration returned a project handle: `True`
- Work-state returned a project: `True`
- Stop result: `RUNTIME: stopped`
- Final classification: `stopped` / `stopped`

Conclusion: this metadata pattern deterministically explains a `stale` status, but it does not reproduce `started -> stale while PID alive`; the current implementation recovers it on the next start.
