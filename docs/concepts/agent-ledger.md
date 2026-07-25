# Agent Ledger

ProcessForge is not the harness. It records the process state around harnesses, agents, and tools.

The agent ledger is the workplace attendance layer. Agents register in `registries/agents.yaml`, check in with `agent-checkin`, refresh presence with `agent-heartbeat`, and check out with `agent-checkout`.

Runtime events are appended to `runtime/agent-ledger/sessions.ndjson`. Current presence is stored in `runtime/agent-presence/<agent-id>.json`. Leases in `runtime/agent-leases/<lease-id>.yaml` are the keys that grant bounded access to a task, capsule, run, and file scope.

Use `agent-availability --role <role> --json` to answer whether the required colleague is actually online without spending agent context on file inspection.
