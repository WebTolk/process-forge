# Runtime workplace state differential

## Compared evidence

- Clean isolated chain: `runtime-lifecycle-clean-repro.md`.
- Current checkout, read-only: `runtime status --workplace . --json`,
  `runtime/pf-runtime/service.json`, presence of `runtime.lock`, and OS PID
  lookup. No live Runtime command that changes state was issued.

## Clean baseline

The clean trace reached `ready`; immediate `session-register` and
`work-state` succeeded. After `stop`, the owned process no longer existed,
the lock was absent, and `service.json` recorded `status=stopped` and
`health=stopped`. The existing contract retains the historical endpoint and
PID in that stopped record, but no longer advertises it as ready.

## Current checkout state

| Signal | Observation |
| --- | --- |
| `runtime status` | `status=stale`, `health=stale` |
| persisted `service.json` | `status=ready`, `health=ready`, endpoint `127.0.0.1:50295`, PID `13064` |
| singleton lock | absent |
| PID 13064 | absent from the OS |
| last state update | 2026-08-14T08:49:53Z |

This is a durable stale-state fixture: a ready record remains after its lock
and process have disappeared. The current shared evaluator classifies that
combination as `stale`, which explains why the command view differs from the
stored JSON. It is not evidence that a fresh current start reported success
before ready.

## Consequence

The clean PASS branch applies: no lifecycle remediation is justified from the
historical symptom alone. The relevant next controlled experiment is to begin
with a clean isolated workplace and add only this metadata pattern (ready
service record, absent lock, dead PID), then add other historical state one at
a time if necessary. It must not clean or mutate the current workplace.

## Shell-worker limitation

The `gpt-5.3-codex-spark` worker completed its assigned read-only report, but
its process resolved a different workplace (`D:\.agents\processforge-workplace`).
Its observations are retained as environment-specific context and were not
used as evidence for this checkout.
