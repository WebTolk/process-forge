# Director, Ledger, Inspector, And Worker Boundary

ProcessForge separates agent coordination from runtime execution inspection.
`supervisor` remains the historical technical CLI name, but the semantic role
is the Process Execution Inspector.

These roles are not mandatory participants in the default single-agent flow.
The atomic unit is one operator, one primary agent session, one project, and one
process/run. In that mode Worker is the same primary agent during execution,
and Inspector is CLI checks, gates, and self-checks. See
[Agent Session Model](agent-session-model.md).

| Responsibility | Ledger | Director | Inspector | Worker |
| --- | --- | --- | --- | --- |
| agent check-in/check-out | yes | no | no | no |
| presence/stale status | yes | reads | no | no |
| grant/revoke lease | no | yes | no | no |
| process route decision | no | yes | no | no |
| handoff accept/return/finalize | no | yes | no | no |
| start/check worker process | no | may ask | yes | no |
| heartbeat/exit/status observation | no | reads | yes | writes |
| required output validation | no | reads | yes | writes |
| perform task | no | no | no | yes |

## Roles

Agent Ledger is the workplace attendance and key registry. It records
check-in/check-out, current presence, stale/offline status, and lease lifecycle.

Agent Director is the coordinator. It reads ledger presence, decides process
routes, grants or revokes leases, moves handoffs through their states, and
prepares continuation work. It may ask the execution inspector for runtime
state, but it must not start shell worker processes or decide success by
looking at a report artifact alone.

Process Execution Inspector is the runtime checker. The compatible CLI names
are `supervisor`, `supervisor-tick`, `supervisor-run`, `supervisor-status`, and
`supervisor-stop`; the clearer aliases are `execution-inspector-tick`,
`execution-inspector-run`, `execution-inspector-status`, and
`execution-inspector-stop`. This role observes assigned task state, starts
approved runtime drivers when configured, checks process/heartbeat/exit proof,
verifies required outputs and expected reports, and marks tasks done or failed.

Worker Agent performs one assigned capsule task and writes the expected outputs
and runtime proof requested by the driver.

## Boundary Rules

The supervisor/execution-inspector code must not grant leases, write workplace
agent ledger events, accept or finalize handoffs, route processes, select
agents, or decide project/run ownership.

The director code must not directly start worker runtime processes, write
`.pf/runtime/agent-runs/**/process.json`, `heartbeat.json`, `exit.json`, or
infer task success from a report artifact. It should call the inspector CLI for
execution state when that state matters.
