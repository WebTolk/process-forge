# Runtime and MCP lifecycle audit

Status: ready_for_review

## Confirmed architecture

- Garage context/search/resolve/work bootstrap already works without a Runtime
  daemon, hooks, Ledger session, or Director.
- PF Runtime is one optional long-lived process per workplace and is required
  only when Forge coordination needs it.
- PF MCP is host-owned stdio: every Codex host connection starts its own child
  process. A detached/autostart MCP process is invalid.
- Windows Runtime autostart is implemented with Task Scheduler. Managed Linux
  `systemd --user` autostart is not implemented.

## Release gaps

- Human quickstarts do not present one-time Codex MCP registration and optional
  Forge Runtime autostart as workstation setup.
- Agent runbooks still advertise manual session/check-in, doctor, index, hooks,
  and low-level run/task commands as the ordinary path.
- The missing-session diagnostic wording still over-emphasizes project-local
  Codex hooks for a generic Garage task.

## Decision

Keep low-level commands for operators and Forge diagnostics. Normal agent work
must use `pf.context -> pf.search -> pf.resolve -> pf.work.start` and report an
operator-level infrastructure blocker instead of installing or repairing PF
Runtime, MCP, host hooks, or Agent Ledger.
