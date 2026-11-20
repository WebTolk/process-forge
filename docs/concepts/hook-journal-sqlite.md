# Project journals in SQLite

Project journals preserve hook acceptance and the facts used by Work checks.
They are private operational data, separate from public artifacts and reports.
Use the [requirements](../requirements.md) for supported SQLite and storage.

The project’s event and hook journals occupy two private SQLite files.

| File | Owner and purpose |
| --- | --- |
| `.pf/runtime/events/events.sqlite3` | `ProcessEventJournal`: unique admissions, optional normalized history, pending hook dispatch, latest verification facts |
| `.pf/runtime/agent-events/hooks.sqlite3` | `RawHookJournal`: native identities, optional raw payloads, pending native input, processing result and quarantine |

Connections are operation-local, use WAL, explicit write transactions,
`synchronous=FULL` and a bounded busy timeout. SQLite serializes writers; this
supports an orchestrator and concurrent local executors without a server.
Use local storage: WAL does not provide a multi-machine network-filesystem
database. DB, `-wal` and `-shm` files are runtime data, never release material.
For a live backup use SQLite's backup API rather than copying only the DB file.

Admission IDs are unique in SQL. Appends never load previous history to find a
duplicate. Indexed methods provide ID/latest/assignment lookups, constant-size
stored counts and keyset pages (`after` sequence, `limit` 1–1000). The cursor
is the last returned sequence and gaps are valid. On a store bound to a
project identity, a library reader needs the configured storage host. Runtime
obtains it through `ProcessEventRecorder.event_journal_for_project`. Opening
such a journal by path alone can return `storage_host_required`. A page read
includes storage checks, the indexed query and decoding the selected records.
Explicit validation, export, migration and rebuild can visit the full history.

Raw acceptance commits before project effects. Cross-owner effects are
recoverable, not one cross-database transaction: deterministic IDs make retry
safe; pending raw input remains until completion; pending project hook dispatch
is retried by duplicate admission or the Runtime tick. External command/API
execution is not introduced by this migration.

`logging.raw_hooks` and `logging.events` follow the effective PFConfig for
the operation, including device, workplace and project settings. Disabling
history preserves minimal admissions, pending work
and latest verification facts. It does not suspend Work or chat delivery. The
existing transcript owner stores conversation bodies; event history refers to
them. These settings do not erase earlier data or promise physical secure erasure.
See [configuration](../authoring/workplace-configuration.md#project-history-and-raw-hooks).

## Other project and workplace storage

Worker execution state has a separate SQL store, by default
`.pf/data/pf.sqlite3`. Work stages, assignments and capsules remain in project
files. The default diagnostic sink writes rotating JSONL in
`.pf/runtime/diagnostics/`. [Execution storage](execution-storage.md) ·
[Diagnostics](diagnostics.md)

The following streams use NDJSON.

| Scope | File | Purpose |
| --- | --- | --- |
| Workplace | `runtime/events/events.ndjson` | Resource and authoring events |
| Workplace | `runtime/agent-ledger/sessions.ndjson` | Agent Ledger session history |
| Project | `.pf/runtime/telemetry/<session-id>.ndjson` | Session telemetry |
| Project | `.pf/runtime/chat/transcripts/session-<identity-digest>.ndjson` | Private conversation messages |

Transcript reads also support the legacy session-named files. Do not feed
these independent streams into the project journal migrator or rename them to
SQLite. See [session telemetry](session-telemetry.md), [chat relay](chat-relay.md)
and [workplace resources](workplace-resources.md).

## Temporary file migrator

`tools/migrate-hook-journals.py` is a temporary PF utility. It imports a project's
legacy `events.ndjson` and only that project's raw records from the former shared
`<workplace>/runtime/agent-events/raw/v1/` shards (or a project-local legacy raw
layout). It preserves IDs, envelopes, source ordering per journal and raw source
locations. Files are streamed; SQL uniqueness detects duplicate/conflicting IDs.
Original files are never rewritten or deleted.

Prepare a controlled cutover: stop old journal writers using the existing
operator lifecycle procedure, back up the source journals, and keep them stopped
until both databases are ready and all consumers use the new Core. The migrator
does not stop/start services, update an installation, or coordinate old writers.
Source hashes, file signatures, source-list stability, SQL counts and integrity
are checked, but those checks cannot prevent a writer resuming after completion.

```sh
python -B tools/migrate-hook-journals.py --project-root <project-root> --workplace <workplace-root>
python -B tools/migrate-hook-journals.py --project-root <project-root> --workplace <workplace-root> --apply
```

Without `--apply`, the utility reports its plan and creates no project database.
Invalid rows block application. After reviewing diagnostics, add `--skip-invalid`
to explicitly omit damaged rows; identity conflicts always fail. Reports contain
private source paths and belong in private operator evidence.

An import commits an `importing` barrier in both databases. Normal reads/writes
refuse an unfinished import. Re-run the same command after correcting the source
or environment to resume; existing matching IDs are not inserted twice. Both
owners become `ready` only after validation. Keep original files frozen after
cutover: later legacy appends are not automatically mirrored into SQLite.

This utility can be removed after the required projects have migrated. Installing
the source changes, migrating real device journals and reconnecting the actual
Runtime/MCP host are separate qualification steps.

SQLite design references: [WAL](https://sqlite.org/wal.html),
[query planning](https://sqlite.org/queryplanner.html),
[UPSERT](https://sqlite.org/lang_upsert.html) and
[Python sqlite3](https://docs.python.org/3/library/sqlite3.html).
