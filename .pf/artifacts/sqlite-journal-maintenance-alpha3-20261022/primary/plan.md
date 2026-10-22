# SQLite and journal maintenance alpha3: parent plan

User explicitly authorizes one complete expensive task, tests/QA, commit/push and
alpha3 prerelease, mode1-1-4, autonomous work then stop. Selected native backlog:
pf-maintenance-sqlite-journals-20261019. Full seven acceptance criteria remain required.

Active scoped Work: garage-sqlite-journal-maintenance-alpha3-scoped-20261022-complete-the-us.
Assignment: sqlite-journal-maintenance-alpha3-scoped-20261022-complete-the-user-auth.
Context: sqlite-journal-maintenance-alpha3-scoped-20261022-complete-the-user-auth-capsule.
Capsule c1f0fa0629356404a97223b89a02a9e09cab8f52d569af7301ce2952732ddbd4.
Fresh ctx-20261021-162229-c46ea2; scope valid/ready. Initial orchestration admission
was cancelled before implementation to pin all current architecture inputs.

One primary orchestrates and integrates; four bounded native codex-exec workers
implement disjoint contributions. One independent native reviewer reads the
finished integrated result only after implementation. Work count describes roles;
start dependent packages after frozen interface readiness. PF Ledger/chat carry
actual handoffs, READ_ACK, RESULT and STOP; workers do not use independent Git.

Ownership:
- Primary: maintenance/contracts.py, Main CLI registration, tests/maintenance_integration,
  version/release/checksums/dist, own primary artifacts/log/scratch.
- W1 backup: maintenance/backup.py and tests/maintenance_backup.
- W2 scanner: maintenance/journal_scan.py and tests/maintenance_scan.
- W3 application: maintenance/journals.py, legacy tools/migrate-hook-journals.py,
  tests/maintenance_service. Reuse W1/W2 interfaces; no Main callback.
- W4 adapter/docs: tools/pf_cli/commands/journal_maintenance.py,
  tools/pf_cli/parsers/journal_maintenance.py, tests/maintenance_cli,
  EN/RU concepts/sqlite-journal-maintenance.md.
- Reviewer: own report/evidence only. No product writer role.

Each worker owns its separate artifacts/log/scratch, exact native assignment and
immutable capsule. Primary preserves existing OOP54–55 Main/resources/platform
WIP. Before-task Main and clean HEAD copies and five foreign hashes retained in
private scratch. Stage only the owned Main delta against original HEAD, leaving
working tree WIP intact. Final acceptance runs in a clean committed candidate;
source checkout evidence and release candidate evidence remain distinct.

Sequence: scope/investigation/domain/architecture; shared narrow contract; native
worker admission/preparation/start; implementation and own targeted QA; integrated
negative/positive tests and quality; independent review and fixes; committed clean
candidate, public release-test and archive qualification; publish alpha3 on both
providers, read back hashes/refs/objects; native closure and stop. No live device
update, Runtime/MCP restart, extra refactor or stable-channel replacement.

Knowledge actually read is recorded in python-oop-guidance.md. ADR/domain/direction,
clarification and migration revision are pinned in the capsule. Use registered PF
pytest/Ruff/format/mypy plus focused coverage/security; preserve existing migration
smokes. Tests must cover real WAL backup, corrupt bytes, explicit skip, conflict,
source drift, replay, incomplete migration, backup tamper, restore and CLI failures.
No new Runtime dependency. Release unit is this complete feature; four workers
are contributions, not four independently published products.
