# Intake and scope

Brief: the user approved designing the shared metadata projection after pf.context latency diagnosis, asks where it lives and how it remains current, and explicitly says not to write code.

Scope: read current Work inventory, summary, selection, pending-completion and YAML publication owners; document shared value model, data ownership, request/process lifetime, content verification, concurrency, memory bounds, legacy semantics and verification plan.

Excluded from this engagement: product implementation, new index files or databases, public API changes, packaging, device updates and service changes. The design may propose later implementation but does not authorize it.

Acceptance: a concrete recommendation about RAM versus files; exact update/invalidation rules for native and external edits; explicit cold-start and consistency limits; preserved live selected Work validation; independent consumer policies; architecture artifact with source pointers, alternatives, rollout and acceptance scenarios. scope-accepted: passed for architecture only.
