# Architecture decisions

2026-10-22. Proposed for future implementation, reviewed against actual PF source and the user's direction.

1. One small neutral accounting module; provider adapters contain schema knowledge; application queries shared by all clients. Reason: same numbers in task report, TUI, plugin and remote CC without embedding UI/HTTP into domain rules.
2. One durable workplace-scoped SQLite store for normalized accounting facts. Reuse suitable existing storage primitives; do not extend optional lifecycle history into the financial source of truth, require Runtime, or introduce a second JSONL ledger.
3. Record source identity/version/quality and exact PF binding, not model-generated self-reports. Modern installed Kimi Code 2.3.0 differs from legacy Python Kimi CLI; treat formats explicitly. Session-scope usage records are not presumed cumulative or discardable.
4. Keep token facts, activity intervals and monetary valuations separate. Currency and basis are mandatory; historical rate versions fixed. A subscription is not automatically allocated by API token prices. No pricing service/FX in v1.
5. Normalize one contribution per proven source unit with replay-safe IDs, revisions/conflict and transactional cursors. No universal reconciliation framework; source-specific grain/cumulative guarantees are qualification requirements.
6. Prepare stable origin IDs, schema version and local sequence for future opt-in REST export. Defer transport/authentication/remote implementation, plugin SDK and TUI framework selection. Never synchronize summed snapshots as additive facts.
7. Current deliverable is planning documentation only; original implementation card stays open with an added immutable input reference. No external workers due capsule deny; assurance is primary self-review and reference checks, not independent review or product qualification.
