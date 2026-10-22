# Accounting assurance plan and cases

Test the public boundaries and failure semantics, using isolated SQLite files and
explicit small provider receipts. Do not use device session-history discovery.

1. Core: measured zero versus unknown, subset token arithmetic, stable occurrence
   identities, repeated identical records, revision order/conflicts and invalidation;
   atomic cursor batches, concurrent writers, schema refusal, reopen and backup.
2. Scope and queries: project/task/run/attempt filters, authorized project sets,
   unassigned versus quarantine, bounds and half-open UTC windows, DTO privacy,
   declared capabilities and explicit incomplete coverage.
3. Time: distinct agents sum; same-agent overlap/nesting; project occupied union;
   independent monotonic/UTC clocks, drift/reversal, clipping, open/crashed tails,
   unknown and lower-bound results. Never infer execution from Ledger presence.
4. Collectors: Codex terminal usage and real sanitized counter fixture, missing
   fields, qualified modern Kimi components, no context/compaction token inference,
   duplicate versus distinct occurrences, partial/torn/malformed bounded streams,
   prefix/binding mutations and cursor replay.
5. Integration: one durable workplace DB across projects, stable project/origin
   mappings, read-only missing-store queries, scope restrictions, CLI JSON/errors,
   failed-accounting behavior preserves report and subprocess exit.
6. Registered Ruff lint/format and scoped mypy on the exact candidate; existing
   codex worker, prepared governance and conversation-completeness smoke tests.
7. Independent native review after implementation. Then qualify that worker's real
   terminal usage, source binding, measured execution and repeated CLI replay.

Primary initial integrated result: 65 tests + 28 subtests PASS; 14-file Ruff checks
PASS; 11-source-file mypy PASS with --follow-imports=silent; all three existing
smokes PASS. QA details and candidate hashes retained. Review/real receipt checks
are separate acceptance gates and were not inferred from synthetic success.

No browser/UI was changed. No release package, installed Core or server restart
is part of this feature cycle. Tests do not establish native Kimi completeness.
