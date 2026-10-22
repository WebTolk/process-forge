# Alpha3 maintenance: executable acceptance cases

The frozen [architecture](architecture.md) defines the test plan. The final
[candidate manifest](source-candidate-r3.json) pins the actual executable cases.

| Responsibility | Executable cases | Observed behavior |
| --- | --- | --- |
| Consistent SQLite backup and restore | `tests/maintenance_backup/test_backup.py` | WAL/concurrent commits, held file identity, integrity/hash checks, bounded waits, refusal to overwrite and cleanup of owned staging |
| Legacy preflight and quarantine | `tests/maintenance_scan/test_journal_scan.py` | Exact invalid bytes/offsets/hashes, counters, duplicates/conflicts, source drift, completed/incomplete provenance and generator closure |
| Application import and recovery | `tests/maintenance_service/test_journals.py` | Explicit skip, verified destination backups, transactional batches, incomplete barriers, idempotent replay, semantic tamper refusal and native NFC identity |
| Operator CLI | `tests/maintenance_cli/test_journal_maintenance.py` | Real argument parsing, JSON/error exits, plan/apply distinction, effects documented in help and real Windows junction refusal |
| Integrated acceptance | `tests/maintenance_integration/test_acceptance.py` | Actual backup/verify/restore, corruption refusal/skip, source preservation, repeat import, recovery and cold composition without Main/Host |
| Released migration adapter | `tools/smoke_hook_sqlite_migration.py` | Existing migration contract, failure injection at the new owners and durable barriers |

[Final test report](test-report-r2.md) and [QA receipts](qa-receipts-r2.json)
record the executed suites, outcomes and unavailable symlink privileges. The
independent [R2 review](../review/r2/report.md) additionally exercised both NFC
orders, ten tamper refusals and five incomplete-quarantine scenarios.

Public source, archive and consumer checks are delivery gates and remain pending
at this assurance checkpoint. Device/connected-host acceptance is separate.
