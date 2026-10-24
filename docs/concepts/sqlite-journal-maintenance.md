# SQLite backup and journal maintenance

`journal-maintenance` is an explicit local operator command over the shared Core
maintenance services. It supports verified single-database backups, safe restore
to a new path, preflight inspection and import of legacy event/raw journals.
Run commands from the source checkout as shown below, or use the corresponding
installed PF entrypoint. All example paths are placeholders.

| Operation | Required options | Persistent effects |
| --- | --- | --- |
| `backup` | `--database PATH --output BUNDLE` | Immediately creates a new verified bundle. |
| `verify` | `--backup BUNDLE` | Validates the existing bundle. |
| `restore` | `--backup BUNDLE --destination NEW_PATH` | Immediately creates a new database. |
| `inspect` | `--project-root ROOT --workplace ROOT` | Checks journals; explicit `--evidence-dir DIR` writes quarantine evidence. |
| `import` | `--project-root ROOT --workplace ROOT` | Plans by default. `--apply` permits import and writes backups/evidence. Explicit `--evidence-dir DIR` can write quarantine during a plan. |

Every operation accepts `--json` and always prints exactly one JSON object to
stdout, including handled operation failures. Exit `0` means success or a usable
plan; exit `1` means refusal, corrupt/tampered input, verification failure or an
I/O error. Argument syntax errors retain argparse's exit `2` and stderr usage;
help exits `0`. Reports contain operator-selected private source and artifact
locations. Store them with restricted maintenance evidence before sharing a
redacted copy publicly. Error codes omit record contents and raw exception text.

## Backup, verification and restore

Choose a new bundle directory whose parent already exists:

```sh
python -B tools/processforge.py journal-maintenance backup --database "DATABASE_PATH" --output "NEW_BACKUP_BUNDLE" --json
python -B tools/processforge.py journal-maintenance verify --backup "NEW_BACKUP_BUNDLE" --json
python -B tools/processforge.py journal-maintenance restore --backup "NEW_BACKUP_BUNDLE" --destination "NEW_DATABASE_PATH" --json
```

`backup` and `restore` write immediately and take no `--apply` flag. Existing
bundle directories and restore destinations are refused. The destination's
parent must already exist. Unsafe symlinks/reparse paths or unexpected bundle
members are refused by the backend.

A bundle contains `database.sqlite3` and `manifest.json`. The source is opened
read-only and copied with SQLite's backup API, including committed WAL data.
Verification checks manifest structure, members, stable SHA256 hashes and SQLite
`PRAGMA integrity_check`. Restore verifies the bundle before creating a new
destination, checks the restored database and retains the backup. Keep the
manifest beside its database; hashes detect changes against that manifest and
provide no independent signature or provenance guarantee.

Each backup is one database snapshot. Backups of multiple databases have
independent snapshot boundaries. Restore produces a separate database file;
installation cutover and selection of active databases use existing operator
procedures.

## Inspect before importing

Use an existing project with `.pf/process-forge.yaml` and an explicit workplace
root. Source discovery reads the project's legacy `runtime/events/events.ndjson`
under its PF flow root, former shared raw shards under the workplace's
`runtime/agent-events/raw/v1/`, and the supported project-local legacy raw layout.
Only raw records for the selected project qualify for import.

```sh
python -B tools/processforge.py journal-maintenance inspect --project-root "PROJECT_ROOT" --workplace "WORKPLACE_ROOT" --json
python -B tools/processforge.py journal-maintenance inspect --project-root "PROJECT_ROOT" --workplace "WORKPLACE_ROOT" --evidence-dir "NEW_QUARANTINE_DIR" --json
python -B tools/processforge.py journal-maintenance import --project-root "PROJECT_ROOT" --workplace "WORKPLACE_ROOT" --json
```

Inspect and import planning leave destination databases unchanged. Without an
explicit evidence directory, these operations create no lasting project evidence.
An explicit directory permits quarantine writes, including when preflight refuses
corruption. `inspect` has no skip option. Invalid rows produce status `blocked`
and exit `1`. Duplicate identity with different content remains an error even
when an import permits invalid rows to be skipped.

Quarantine preserves each invalid line's exact bytes, including NUL and line
endings. `manifest.json` records source, line number, byte offset, byte length,
SHA256, reason and the corresponding `records/*.bin` member. The report supplies
the manifest path/hash. Existing identical evidence is reusable only after
verification; conflicting evidence is refused. Keep the manifest and binary
members together, along with the unchanged source journals and operator report.

If scanning stops after capturing corruption, the retained
`manifest.incomplete-*.json` preserves the captured bytes and provenance with
`scan_complete: false` and a failure code. It does not certify the full source
scan. A completed manifest from an earlier pass stays intact. Import failure
evidence marks incomplete preflight explicitly; its counters do not certify a
complete scan. Identity conflicts and source drift still require investigation.

## Explicit import and repeat execution

Coordinate the cutover of legacy journal writers through existing operator
procedures before applying. Review the plan and retain originals and evidence.

```sh
python -B tools/processforge.py journal-maintenance import --project-root "PROJECT_ROOT" --workplace "WORKPLACE_ROOT" --apply --evidence-dir "MAINTENANCE_EVIDENCE_BASE" --json
```

Applying creates a unique operation directory under the explicit evidence base,
or under the project's `.pf/runtime/journal-maintenance/` by default. It preserves
invalid bytes even when import is refused. It creates verified backups of each
existing destination database before mutation and records missing destinations.
The destinations are `runtime/events/events.sqlite3` and
`runtime/agent-events/hooks.sqlite3` under the project flow root.

Skipping corruption requires an explicit operator choice after reviewing it:

```sh
python -B tools/processforge.py journal-maintenance import --project-root "PROJECT_ROOT" --workplace "WORKPLACE_ROOT" --apply --skip-invalid --evidence-dir "MAINTENANCE_EVIDENCE_BASE" --json
```

`--skip-invalid` also works with a plan, and never implies `--apply`. Valid IDs and
original envelopes are preserved. Successful import checks source stability,
SQLite integrity, unique IDs/counts, migration state and semantic replay. Repeating
the explicit import uses existing journal deduplication; already present records
are reported rather than inserted twice. Each applied attempt retains its own
evidence and backups.

The import report's `counts` distinguishes `read`, `valid`, `imported`,
`already_present`, `skipped` and `corrupted`. Inspect also reports `read_rows`,
`valid_rows`, `invalid_rows`, `skipped_rows`, `duplicate_rows`, blank/filtered rows
and per-kind totals. Valid rows include duplicates. Skipped import counts include
other-project raw records and corrupt rows only when skip was explicit; inspect
reports filtering separately. Corrupted records remain corrupted in evidence.

An interrupted import retains incomplete migration barriers and recovery evidence.
Use the retained phase/failure reports to review destination state before an
explicit retry. Required backup/evidence/verification failures remain failures.
Source drift or identity conflicts require operator investigation; there is no
force option or automatic source rewriting.

## Maintenance boundary

Maintenance preserves source journals and historical PF artifacts. It does not
repair project contexts, create/resume historical Work, change grants, update an
installation, or start/stop Runtime, MCP or other services. SQLite source/hash
checks detect observed changes; operator procedures control the writer cutover.
This CLI adds no MCP endpoint or shell passthrough.

The existing `tools/migrate-hook-journals.py` keeps its explicit plan/apply/skip
entrypoint as a thin delegate to the same maintenance service; its optional
`--evidence-dir` selects evidence storage. See
[Project journals in SQLite](hook-journal-sqlite.md) for journal ownership and
cutover context.

## Execution storage engine (R02 source slice)

The execution engine imports observable latest `status.json` snapshots into the
project main store. It preserves explicit project/run/task/attempt identity,
unknown compatibility fields and exact original bytes. Numeric attempt directory
names set allocation floors; their bodies are never used to invent history.
Directory-only attempts without an observable head refuse cutover, preventing
reuse of a previously prepared attempt number. Historical completeness is not
claimed. Unknown/current activity, ambiguous names, source drift, foreign schemas
or an absent explicit manifest `project.id` refuse migration.

`ExecutionMigrationService` takes the frozen database/repository/admission/backup
dependencies and the private typed `safety` verifier. Its
`ExecutionMigrationContext` pins authorized project/workplace routing, project and
store identity, target, generations, plan and whole-inventory checksum. The host
must exclude old writers, pre-spawn gaps and all owned process trees, and verify
the exact Runtime instance/routing/capabilities. Freeze, resume and pre-cutover
proof checks run under admission; stale/missing/exception/active/unknown proof
fails closed. `offline_confirmed` records operator intent only. No technical
fencing of arbitrary old binaries is claimed.

Inspect/plan do not create a database or binding. Explicit evidence is contained
under the selected flow root's `maintenance/` directory. The manifest is streamed
in raw UTF-8 relative-path order; only 256 directory names or import records are
buffered. Read-only sorting may repeat directory passes for large fanout. Bodies
are bounded to 64 KiB; stdout/stderr, reports and prepared inputs are never read.
Only positively historical invalid snapshots with full host quiescence proof may
be skipped; exact bytes, hashes and provenance remain in evidence.

Apply publishes a pending `data/execution-storage.json` binding under admission
before database mutation. An existing store receives one verified WAL-aware
recovery backup. Import plus its checkpoint commits in batches of at most 256.
Schema/source/count/FK/replay checks precede cutover. A separate, deterministic
`verification/` bundle reuses BackupPort to check SQLite integrity without
bypassing the public SQL session's prohibition on administrative PRAGMAs. Resume
verifies and reuses both evidence bundles; the verification snapshot never
replaces the pre-mutation recovery backup. SQL `execution_state` and the migration
ready marker change together in the sole CAS authority cutover.

Exact `migration_id`, `plan_checksum` and evidence select resume. Pending binding
blocks capable execution clients; there is no JSON fallback. After committed
cutover, resume repairs only the derived report and leaves indexed dirty heads
for the existing projection owner. Later status.json changes are never imported
as truth. Explicit `abort` removes only this engine's pending binding before any
target/schema mutation. Once import/schema commits exist, recovery rolls forward;
restore requires a new target and a controlled offline binding switch.

The command/parser adapters add `execution-inspect`, `execution-import` (plan by
default) and `execution-resume`. Apply needs `--apply --offline-confirmed` and
`--evidence-dir`; resume additionally requires exact migration/checksum selectors.
They emit one JSON object, with exit 0 for plan/ready, 1 for refusal and argparse 2
for invalid syntax. Without host composition/verifier they fail closed.

## Native UUID coordinator and automatic hooks

`StorageMigrationService` is the common native update/first-write/resume service.
`tools/migrate-storage.py` takes explicit `--project-root` and/or
`--workplace-root`, optional `--device-config`, and mutually exclusive `--inspect`
(default), `--apply`, `--resume`. `--json` retains exactly one JSON result;
exit codes are 0 for planned/ready, 1 for deferred/refused/failed, argparse 2.
There is no CLI safety override. The host supplies an operation-pinned full
`ConfigurationProvider` and exact authorized targets; one snapshot is passed to
all dependencies without another merge. No agent, LLM, network or daemon is used.

The host calls `ensure_ready(context, trigger='update'|'first_write')` before a
mutating operation, and after terminal reconciliation/collection only after task,
target and SQL locks are released. Active/unknown before any pending pin returns
`legacy_allowed=true` for that target without minting a UUID or creating migration
files. Pending always requires exact recovery, never legacy/JSON fallback. A
changed/unavailable safety generation refuses. Pure reads, configuration, doctor
and the 500 ms guard never call the coordinator.

Recognized existing events/raw/accounting/search stores receive only
`pf_store_meta`, `pf_schema_versions` and `store_identity@1`. Their original
application IDs, versions, domain SQL/constraints/indexes/FTS shadow objects,
rows/IDs/blobs and paths remain unchanged. Exact qualified schema fingerprints
are in `schemas/storage-migration-v1.json`; extra/foreign/future/drifting objects
refuse. The search baseline is meta version 6, application_id/user_version 0/0.
This is qualification of specific schemas, not all historical releases.

Project owners require explicit manifest project.id. Accounting checks its
existing `data/accounting/identity.json` origin_id. Other workplace targets require
a stable identity from a qualified host metadata source; a directory name or new
ID is insufficient. Main keeps the strict W2 envelope and only its execution
binding; no second legacy identity pin is created for main.

Each owner has `data/storage-identities.json`, with slots pinning kind, relative
target, scope/owner, UUID, state and plan checksum. An exact target selector first
persists its UUID in `data/storage-migrations/r02-storage-v1/targets/`; its immutable
plan and journal live under the checksum directory. No newest/first journal
selection or UUID remint is permitted. Pending publication precedes mutation.
A verified WAL backup is related to the source logical/schema fingerprint and
plan before metadata commits. Streaming typed row digests, counts, integrity and
FK checks prove parity; metadata is excluded from domain digests. Resume verifies
the same backup and source facts, including after a metadata commit with a stale
file journal. Each target commits independently; an already-ready target is not
rolled back when a later target fails. Original backup bytes are retained.

`storage_identity_access` holds the owner identity gate from before adapter open
through connection close. Ready verifies pinned UUID/owner/domain schema; pending
refuses, and unpinned metadata never remints. Internal backup uses the raw injected
driver without recursively entering migration. `new_store_identity` fences an
explicit writable initializer and publishes pending before file creation;
`add_store_identity` adds metadata inside its domain initialization transaction.
A failed initializer retains pending; retry uses the same UUID. Inventory never
creates absent unused stores. Rebuild must preserve UUID or use controlled rebind;
backup/restore preserve it.

The coordinator delegates execution snapshots, checkpointed import and the sole
SQL authority CAS to the frozen `ExecutionMigrationService`. It does not invent
history or duplicate that engine. Main resume uses a durable exact plan selector;
after cutover SQL stays authoritative and projection repair belongs to its owner.

The script consumes `composition.build_configuration_provider` and
`composition.build_storage_migration_host`. The latter must pin enrollment,
installed code/capabilities, instance/routing, old writer exclusion, pre-spawn
publication gaps and complete trees, then inject both storage and execution
verifiers. Its absence is a bounded `storage_host_factory_unavailable` refusal.
Script/automatic policy tests with injected fixture proof do not establish real
host exclusion. Actual W3 composition, installed update/first-write qualification
and integrated assurance are separate gates; this source slice performs no live
migration or infrastructure actions.
