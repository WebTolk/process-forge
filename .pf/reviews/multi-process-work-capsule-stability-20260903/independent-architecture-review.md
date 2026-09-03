# Architecture Review: Multi-Process Work Capsule Stability

Verdict: accepted with one follow-up.

Reviewed boundary: project snapshot authorizes a compact allowlist; `pf.work.start` selects one process; the assignment capsule pins only that process, active specializations, selected resource IDs, snapshot ID/checksum, and process fingerprint. Completion returns an advisory for a new Work instead of transferring context through a session.

Accepted points:

- Legacy singular `process` continues as a one-process selection.
- Invalid default cannot add itself to `allowed`.
- Explicit unknown and explicit disallowed selections are distinguishable.
- Process routes may provide an allowed next-process recommendation without opening or changing the next Work.

Follow-up: candidate descriptions are resolved at choice-render time. They are compact in the response and never persisted in the capsule, but a future snapshot catalogue could cache compact metadata to avoid that lookup.

Review method: source-level review by the primary agent because no separate reviewer session was available in this host; focused behavioural smoke provides the independent executable signal.
