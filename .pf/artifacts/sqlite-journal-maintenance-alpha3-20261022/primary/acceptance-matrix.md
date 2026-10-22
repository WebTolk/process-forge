# Original seven acceptance criteria

| Criterion | Actual evidence | Result |
| --- | --- | --- |
| Consistent SQLite backup, verified manifests/checksums/integrity | maintenance_backup tests, verified native ZIP/sidecar and source/archive profiles | PASS |
| Preflight with source/line/offset/reason, unchanged originals | maintenance_scan and integrated real-file assertions | PASS |
| Exact corrupt bytes, provenance and SHA256 | complete and incomplete quarantine cases, including conflict/drift/closure | PASS |
| Explicit skip-invalid and truthful counters | refusal without consent, explicit apply/skip, service and real CLI cases | PASS |
| Integrity/state/semantic replay, idempotency and verified restore | maintenance_service/backup/integration suites and native migration smoke | PASS |
| Valid input, NUL corruption, refusal, repeat and restore | 145 component tests/65 subtests plus final whole-suite inclusion | PASS |
| Operator boundaries and evidence retention | EN/RU concepts/sqlite-journal-maintenance.md, release notes, final handoff | PASS |

Final whole pytest: 530 passed, 7 environment skips; real NTFS junction cases pass.
Registered lint/format/strict typing/Bandit pass. Independent R3 CODE GO verifies
the cumulative candidate; R1 mandatory findings and the first public-gate failure
remain recorded. Source/archive/publication receipts bind the actual delivered bytes.
