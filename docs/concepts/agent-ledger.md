# Agent Ledger

ProcessForge is not the harness. It records the process state around harnesses, agents, and tools.

The agent ledger is the workplace attendance/session layer. It is not a
separate agent. In Forge/factory operation, supported Codex/Kimi hooks normally
deliver lifecycle and activity automatically through Host to Ledger. Newly
admitted prompt, compaction and tool activity refresh the exact authorized
session without periodic LLM calls. Explicit `agent-heartbeat` /
`session-heartbeat` CLI and MCP operations remain manual compatibility APIs;
`agent-checkin` / `session-start` and `agent-checkout` / `session-end` remain
available to operators.

Hook admission preserves registry, provenance, project and session ownership
checks. Unknown/raw-only, rejected, duplicate and replayed input does not refresh
presence; activity does not reopen a checked-out session or extend a lease.
Raw hook history may be disabled without disabling supported normalized delivery.
No heartbeat is synthesized during silence. Session activity is separate from
execution receipts and proof of OS process/tree ownership or completion.

Local-only Garage does not require Runtime, hooks or Ledger. Automatic delivery
depends on effective provider hook registration and Host configuration; source
behavior alone does not verify registration or qualify a particular device.

Runtime events are appended to `runtime/agent-ledger/sessions.ndjson`. Current
presence is stored per session under
`runtime/agent-presence/<agent-id>/<session-id>.json`, so one `agent_id` may
have multiple active sessions across projects or terminal windows. Leases in
`runtime/agent-leases/<lease-id>.yaml` are the keys that grant bounded access
to a task, capsule, run, and file scope.

Use `agent-availability --role <role> --json` to answer whether the required colleague is actually online without spending agent context on file inspection.

The ledger records attendance, presence, stale/offline status, and lease
lifecycle. It does not think, decide, route processes, accept or finalize
handoffs, start worker processes, or validate task outputs. The Director reads
ledger state to coordinate work; the Execution Inspector reads task/runtime
state to verify execution. See [Agent Session Model](agent-session-model.md) and
[Director, Ledger, Inspector, And Worker Boundary](director-ledger-inspector-boundary.md).

The ledger is workplace-scoped but distinct from the private Raw Event Journal.
Raw ingress can create derived session/telemetry effects only after project
scope validation; it does not make the Ledger a copy of every raw payload.
