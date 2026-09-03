# Codex Fresh Session Bootstrap Audit

Generated: 2026-08-24 12:00 +04

## Finding

Project-local Codex hook installation is present and complete in static
configuration:

- `project-init-status` reports `codex_integration.status: installed`;
- all expected events are registered, including `SessionStart`;
- the managed target is `.codex/hooks.json`;
- no missing hook events were reported.

## Not Proven

A genuinely fresh Codex SessionStart cannot be produced from this already
running Codex worker. The current evidence proves installed configuration, not
that Codex has reloaded the project-local hook file and emitted a new
SessionStart into ProcessForge Ledger.

## Required Acceptance Gate

Open a new Codex session in this project after hook installation and verify:

1. raw hook ingress receives `SessionStart`;
2. normalized Ledger records the same real session id;
3. `pf.session_context` works without manually invented session ids;
4. no fallback fake session id is created.

Status: `partial`.
