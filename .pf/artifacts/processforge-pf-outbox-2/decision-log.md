# Decision Log

| Decision | Rationale |
|---|---|
| Use assurance mode for the audit | No product code changes are required to verify hook recording; code path inspection and outbox sampling are sufficient. |
| Do not modify `.pf/hooks.yaml` | Configuration already enables outbox target and disables network by default, matching project policy. |
| Do not run full smoke suite | Audit scope is bounded to previous work and hook status; smoke suite is already covered by other Work. |
| Defer live Kimi hook verification to a future Work | Requires a Ledger-bound session and explicit operator authorization; not part of this audit scope. |
| Preserve existing outbox contents | Historical payloads are evidence; no cleanup without a dedicated policy. |
