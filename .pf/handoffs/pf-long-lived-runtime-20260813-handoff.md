# Handoff: PF Long-Lived Runtime

## Status

Done. The lazy `runtime-host` PoC has been extended with a user-mode, workplace-scoped long-lived runtime process exposed as `pf runtime ...`.

## Primary Entry Points

- `pf runtime serve --workplace <workplace>`: foreground service.
- `pf runtime start --workplace <workplace>`: background service.
- `pf runtime stop|restart|status|doctor --workplace <workplace>`: lifecycle and diagnostics.
- `pf runtime event|session-register|project-state|work-state|resolve|tick --workplace <workplace>`: loopback IPC-backed operations.
- `pf runtime-host ...`: retained direct Core fallback.

## Runtime State

Runtime service state is under:

- `<workplace>/runtime/pf-runtime/service.json`
- `<workplace>/runtime/pf-runtime/runtime.lock`
- `<workplace>/runtime/pf-runtime/token.json`
- `<workplace>/runtime/pf-runtime/logs/operator.log`
- `<workplace>/runtime/pf-runtime/logs/runtime.stdout.log`
- `<workplace>/runtime/pf-runtime/logs/runtime.stderr.log`

The runtime listens on `127.0.0.1` with a per-workplace bearer token and enforces a `1 MiB` request body limit.

## Adapter Contract

Adapter-neutral planning is captured in `.pf/artifacts/pf-long-lived-runtime-20260813/adapter-contract.md`.

Codex hooks are the first concrete adapter source, using `.pf/artifacts/pf-runtime-director-ledger-20260813/codex-events-reference.md`. Other agents should implement the same normalized event boundary by setting `source.adapter`, `session_id`, and `project_root`/`cwd`, and by keeping native agent details inside `payload`.

## Validation Evidence

Passed:

- `python tools/smoke_long_lived_runtime.py`
- `python tools/smoke_runtime_host_poc.py`
- `python tools/smoke_agent_ledger.py`
- `python tools/smoke_agent_director_tick.py`
- `python tools/smoke_process_supervisor_tick.py`
- `python tools/validate-process-forge-schemas.py --root .`
- `python tools/validate-public-cleanliness.py --root .`
- `python tools/processforge.py events-validate --project-root .`
- `python tools/processforge.py runtime --help`

Known non-runtime residual:

- `python tools/validate-process-forge-checksums.py --root . --check` fails because checksum inventory is stale. This includes older release files and new runtime files. Refreshing checksum inventory should be handled in release-delivery, not hidden inside this implementation pass.

Self-hook test:

- Runtime was started on `D:\.agents\processforge-workplace`.
- Creating `.pf/artifacts/pf-long-lived-runtime-20260813/self-hook-runtime-test.md` from the active Codex session did not produce Codex hook events in `.pf/runtime/events/events.ndjson`.
- Manual normalized adapter ingress did append `agent.tool.completed`, proving runtime ingress is functional.
- Confirmed blocker for real self-observation: no Codex lifecycle hook adapter is loaded in the current Codex config/session.

## Follow-Up

- Build the live Codex hook adapter that maps hook JSON to `pf runtime event` and falls back to `pf runtime-host event` or durable outbox when the runtime is unavailable.
- Decide whether projection rebuild should become a periodic job or remain explicit until the outbox/projection contract is finalized.
- Run full `release-test` after checksum inventory refresh.
