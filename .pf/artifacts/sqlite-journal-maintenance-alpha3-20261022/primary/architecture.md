# Maintenance alpha3: architecture, frozen worker interfaces and acceptance

This bounded feature applies D01/D02/D03/D06/D07/D09/D11 and R01–R12. Current
clarification/migration revision constrain the older optional Kernel/DI proposals.
Shared maintenance services own I/O and ordering; thin CLI adapts arguments/JSON.
Patterns: existing repositories, injected operation ports, application service,
CLI/legacy adapters and immutable value receipts. No global current project,
constructor I/O, service locator, Host launch or Main callback.

## Shared contract

Primary writes maintenance/contracts.py with JsonObject = dict[str, Any],
SourceKind = Literal["events", "raw"], JournalSource = tuple[SourceKind, Path],
JournalRow = tuple[SourceKind, JsonObject, str], MaintenanceError(ValueError)
(code available as .code), BackupPort and JournalScanPort protocols. Any is only
for existing JSON payload values, never a universal Core dependency.

W1 module maintenance/backup.py exports SQLiteBackupService with cold defaults:
create(source: Path, bundle: Path) -> JsonObject;
verify(bundle: Path) -> JsonObject;
restore(bundle: Path, destination: Path) -> JsonObject.
Methods return JSON-compatible reports with status and artifact/hash/integrity
facts. Bundle directory is new/exclusive and contains database.sqlite3 plus
manifest.json. Never overwrite an existing bundle or restore destination. Source
is opened read-only and copied with Connection.backup (WAL/concurrent commits
included), not shutil/copy of live DB. Verify manifest/schema/member containment,
regular non-symlink files, stable hashes and PRAGMA integrity_check before success.
Restore verifies first, creates a new destination, checks integrity, and retains
original backup. Bound waits; clean only own failed staging. No source mutation,
file grants, connection to arbitrary SQL hosts or global multi-DB transaction.

W2 module maintenance/journal_scan.py exports JournalScanService:
discover(project: Path, workplace: Path) -> tuple[Path, list[JournalSource]];
rows(sources: list[JournalSource], project: Path, report: JsonObject, *,
     skip_invalid: bool = False, quarantine_dir: Path | None = None)
     -> Iterator[JournalRow];
preflight(project: Path, workplace: Path, *, skip_invalid: bool = False,
          evidence_dir: Path | None = None) -> JsonObject.
Preserve existing source discovery/filtering/identity/conflict behavior. Report
retains existing fields sources, events_rows, raw_rows, unique_events, unique_raw,
invalid, blocked, other_project_raw, diagnostics; add unambiguous read/valid/
invalid/skipped/duplicate counters and quarantine evidence. Keep byte offsets and
raw line bytes including newline/NUL. Invalid data never becomes fake valid data.
When evidence_dir is explicit, save exact invalid bytes, stable source/line/offset/
length/SHA256/reason metadata and a verifiable quarantine manifest. Idempotent
same-byte existing evidence may be reused only after verification; never overwrite
conflicting evidence. No invalid payload in public errors. Source signatures and
full hashes checked between passes. Pure native identity validation may be a
narrow injected adapter to existing primitives; no Main/Host import.

W3 module maintenance/journals.py exports JournalMaintenanceService with injected
BackupPort/JournalScanPort and cold concrete defaults. Public method:
migrate(project_root: Path, workplace: Path, *, apply: bool = False,
        skip_invalid: bool = False, evidence_dir: Path | None = None) -> JsonObject.
A plan has no DB mutations. Applying preserves originals, quarantines invalid
rows even when refusing import, and refuses invalid input unless skip_invalid is
explicit. Evidence path defaults under project .pf/runtime/journal-maintenance
with a unique operation namespace only when apply=True; report its private
location honestly. Before DB mutation, create verified backups of each existing
destination DB using W1; missing destinations are recorded. Reuse existing
ProcessEventJournal/RawHookJournal migration/dedup/transaction controls. Retain
incomplete barrier on interrupted import. Check source drift, PRAGMA integrity,
unique valid IDs/counts and semantic replay without duplicate insertion. Report
read/imported/already-present/skipped/corrupted counts, migration state and backups.
No silent cleanup/import repair, force guard, source rewrite or task lifecycle.
Keep tools/migrate-hook-journals.py CLI flags/exit behavior as a thin delegate;
new optional evidence-dir is additive. Public library uses no imported Main.

W4 new CLI group journal-maintenance via new parser/command modules. Subcommands:
backup --database PATH --output BUNDLE;
verify --backup BUNDLE;
restore --backup BUNDLE --destination NEW_PATH;
inspect --project-root ROOT --workplace ROOT [--evidence-dir DIR];
import --project-root ROOT --workplace ROOT [--evidence-dir DIR]
       [--apply] [--skip-invalid].
All support --json and return a single JSON object. backup/restore are explicit
local operator mutations; import is plan-only without --apply. New error mapping:
exit0 success/planned, exit1 blocked/invalid/tampered/I/O failure. No MCP tool or
shell command passthrough. Parser registration is a standalone register function;
primary owns importing/calling it in Main to preserve dirty baseline. CLI composes
actual defaults, not callbacks through Main. Keep side-effect classification
truthful in help/docs; public sample paths are placeholders.

## Worker duties and QA

W1/W2 may implement independently after this interface. W3 composes both and W4
adapts public interfaces; defer dependent tests until imports are available, without
placeholder implementations. Report readiness/missing interfaces to primary.
Only owned files may be changed. Do not edit Main/checksums/version/Git/others.
Each worker adds meaningful behavior and failure tests in its owned test directory,
runs applicable registered pytest/Ruff format/lint/mypy (coverage/security where
useful), records exact commands/exit/hashes and public API. Each contribution
uses native lifecycle and required exact selectors; report after implementation,
then remain alive at code-assurance for review fixes until primary STOP. Use own
Ledger session and send PF READ_ACK/RESULT to the primary session. Primary sends
STOP only after final integration/review and worker contribution closure is safe.

Independent reviewer begins after all four implementations and integrated checks
are ready. Verify corruption integrity, source immutability, safe paths/restore,
concurrency and durable barriers, old CLI behavior, ownership/import boundaries,
no default global state and actual tests. Must-fix findings require repair and
repeat review; initial and revised reviews stay immutable.

Primary integration tests cover all original seven task criteria, clean library
import without Main/Host, real CLI flows, WAL/concurrent source backup, explicit
refusal/skip NUL record, quarantine byte/hash comparison, import twice, failure/
source change, verified restore and old migration smoke. Run registered QA and
meaningful coverage of new owners; do not invent 100% product coverage. Apply
release/schema/cleanliness/checksum/public suite and archive qualification to
clean committed alpha3 candidate with no unrelated WIP. Distinguish source,
clean archive/consumer installation from actual device/connected-host acceptance.
