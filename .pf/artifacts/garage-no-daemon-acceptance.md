# Garage No-Daemon Acceptance

Status: partial pass

`tools/pf_runtime/codex_hooks.py` already falls back to durable Host/Core
ingestion when Runtime `/event` is unavailable. This supports Garage operation
without a required long-lived Runtime.

Validated indirectly:

- `python tools/smoke_codex_integration.py`
- `python tools/smoke_project_init_codex_integration.py`

Residual: no full fresh Codex no-daemon end-to-end session was started in this
turn.
