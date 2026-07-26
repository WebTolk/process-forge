# Agent Ledger

ProcessForge is not the harness. It records the process state around harnesses, agents, and tools.

The agent ledger is the workplace attendance/session layer. It is not a
separate agent. Agents register in `registries/agents.yaml`, check in with
`agent-checkin` or `session-start`, refresh presence with `agent-heartbeat` or
`session-heartbeat`, and check out with `agent-checkout` or `session-end`.

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
