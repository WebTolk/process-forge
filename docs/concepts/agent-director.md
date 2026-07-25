# Agent Director

Agent Director is a ProcessForge process and CLI layer. It is not WT AICC and not a web UI.

`agent-director-tick` performs one deterministic scheduling pass: inspect pending handoffs, check agent availability, grant leases, mark a handoff ready, keep it waiting when no role is online, and mark expired leases stale. Bounded `agent-director-run` repeats the same tick.

The Director uses the workplace ledger and presence files. It does not start real external agent ecosystems in public tests.
