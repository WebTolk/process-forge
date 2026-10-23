# Applied PF Python and OOP guidance

Read the actual pinned python-source-excerpts.md before implementation. These are
current excerpts exported from PF Work-resolved docs.python, docs.python-practices
and docs.python-peps; provenance hashes/line spans are in the companion JSON.

Use composition, explicit dependencies and one cohesive responsibility per owner.
Protocols describe actual used methods, never the entire legacy facade. Frozen
dataclasses suit configuration/value identity; do not freeze mutable job state by
accident. Keep imports canonical, constructors cold, request data operation-local,
resource/connection ownership explicit and cleanup in finally/context managers.
No broad exception masking of durable writes. Use precise typed boundaries, PEP8,
PEP257 and useful Google-style docs. Tests exercise success, refusal, concurrency,
crash/retry and access invariants rather than mirror the implementation.

File-only native worker contract: no external workplace roots or QA installation,
no Git, PF lifecycle or infrastructure commands. Primary owns registered QA and
Ledger/chat forwarding. Emit actual READ_ACK after reading frozen inputs, then
implement only own files; report exact tests run and limits. Local stdlib checks
may use only your own scratch. Never claim primary's pending QA as your own result.
