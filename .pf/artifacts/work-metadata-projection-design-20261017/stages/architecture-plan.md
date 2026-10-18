# Architecture plan

Artifacts: architecture.md, implementation-plan.md, decision-log.md, review.md. Proposed solution: existing content-addressed parse cache holds compact fields in RAM; one explicit immutable read-pass snapshot serves summary/catalog; YAML authority, different consumer rules and exact live selected reads remain.

Storage/freshness, source ownership, pending completion, read-after-write, concurrency, cold start, bounded memory and alternatives are specified. No persistent index, Runtime dependency, new error/permission protocol or product implementation is introduced. Future validation conditions are explicit and not claimed complete. Architecture-plan-ready: passed for delivery of a design only.
