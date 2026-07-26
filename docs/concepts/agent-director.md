# Agent Director

Agent Director is a ProcessForge process and CLI layer. It is not WT AICC and not a web UI.

Agent Director is not required for the default single-agent `1-1-1-1` flow.
That flow is one operator, one primary agent session, one project, and one
process/run. Director appears when ProcessForge composes multiple agent
sessions or multiple process runs through routes, handoffs, leases, and
continuations.

`agent-director-tick` performs one deterministic scheduling pass: inspect pending handoffs, check agent availability, grant leases, mark a handoff ready, keep it waiting when no role is online, and mark expired leases stale. Bounded `agent-director-run` repeats the same tick.

The Director uses the workplace ledger and presence files. It does not start
worker runtime processes, write `.pf/runtime/agent-runs/**/process.json`,
`heartbeat.json`, or `exit.json`, or infer task success from a report artifact.
When execution state matters, it asks the Process Execution Inspector through
`execution-inspector-status`, `execution-inspector-tick`,
`execution-inspector-run`, or the compatible `supervisor` commands.

The Director does not start real external agent ecosystems in public tests. See
[Director, Ledger, Inspector, And Worker Boundary](director-ledger-inspector-boundary.md).
