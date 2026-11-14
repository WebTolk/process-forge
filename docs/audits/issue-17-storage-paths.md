# Supported storage paths and recovery qualification

This inventory records implemented entrypoints at the issue #17 qualification
boundary. A listed path requires its stated ownership and safety evidence.
Neither source tests with injected host proof nor UUID metadata qualify a deployed
old-writer boundary. PF Core maintenance and package lifecycle have different
owners: package updates do not request workplace-wide Core maintenance.

The project flow root is selected explicitly. Its main profile defaults to
`project_main` at `data/pf.sqlite3`; an authorized profile alias must match the
existing execution binding. Project identity comes from the explicit manifest
`project.id`, never a directory name.

| ID | Entry and implemented transition | Authority and recovery |
| --- | --- | --- |
| ST01 | `select_execution_storage`: attach an existing ready main through its exact binding/profile. | Preserve project/store identity. Pending, missing, foreign or conflicting bound storage refuses without JSON fallback. Read access creates nothing. |
| ST02 | `storage_identity_access`: attach a recognized ready events/raw/accounting/search store through its owner slot. | Hold the owner identity gate for the adapter connection. Verify UUID, scope/owner, kind/path and domain schema. Pending and unpinned adopted metadata refuse. |
| ST03 | `migrate-storage.py --apply`, update/first-write coordinator: adopt UUID metadata in place in a recognized legacy database. | Preserve domain IDs, rows, blobs, schema objects and path. Active/unknown safety before pending defers without UUID minting or history scan. Exact selector/plan/pending precede mutation. |
| ST04 | `migrate-storage.py --resume`: recover the exact adoption plan. | Reuse UUID, descriptor, source facts, backup and generation. A metadata commit with a stale file journal rolls forward. Targets commit independently; a later failure does not undo a ready target. |
| ST05 | `journal-maintenance execution-import`, coordinator main import: latest execution snapshots and allocation floors into main SQL. | Require qualified quiescence and old-writer exclusion. Publish pending binding first. Batches are at most 256; import and checkpoint share a transaction. A single ready/sql CAS establishes authority. No invented overwritten history. |
| ST06 | `execution-resume`, coordinator main recovery. | Use exact migration/checksum/evidence selectors and retained backup/checkpoint. Recheck frozen sources and safety before cutover. After ready, SQL remains authority; JSON is only a projection. |
| ST07 | `new_store_identity` plus `add_store_identity`: initialize an explicitly new writable domain target. | Pending precedes creation; metadata shares the domain initialization transaction. Interruption retains the same UUID. Inventory does not create unused absent stores. |
| ST08 | Explicit successful new-flow initialization: fresh main SQL publication. | Existing or forced initialization is not fresh by inference. A durable pending initializer closes legacy routing even before binding publication. Repair uses its exact owner/UUID/profile and qualified native capability. |
| ST09 | Offline move of the complete project with unchanged relative bindings. | Preserve project/store identity, accepted resources, relative paths and profile. This is not arbitrary live rebind. The maintained engine test covers rename with injected host dependencies; real physical relocation still needs deployment qualification. |
| ST10 | `journal-maintenance backup/verify/restore`: one SQLite snapshot to a verified bundle and a new absent destination. | Include committed WAL, preserve UUID/data and retain the bundle. Existing/unsafe/tampered destinations refuse. Restore does not switch live binding. Several database snapshots are independent. |
| ST11 | `journal-maintenance inspect/import`, legacy `migrate-hook-journals.py`: recognized events/raw journals to project journal databases. | Preserve IDs/envelopes, originals, quarantine and backups. Operator procedures own writer cutover. Drift/conflicting duplicate refuses even with skip-invalid; interrupted apply retains an incomplete barrier for explicit retry. |
| ST12 | Managed PF Core update or qualified first cold transition, followed by fresh installed-code maintenance. | Core publication and storage readiness have separate acceptance. Retain exact selection, epoch, store UUID/bindings and recovery owner. Linux controlled-cohort and baseline-fence primitives alone do not implement or qualify the full transition. |

## Recognized target layouts

Paths below are relative to the selected project flow root or workplace root.

| Scope / kind | Path | Stable owner source |
| --- | --- | --- |
| Project events | `runtime/events/events.sqlite3` | Explicit manifest project ID |
| Project raw | `runtime/agent-events/hooks.sqlite3` | Explicit manifest project ID |
| Standalone project search | `runtime/local-resource-search/search.sqlite` | Explicit manifest project ID; selected only without a workplace |
| Project main | `data/pf.sqlite3` or the exact selected profile alias | Explicit manifest project ID; execution binding rather than a second legacy pin |
| Workplace raw | `runtime/agent-events/hooks.sqlite3` | Stable ID in the selected workplace manifest |
| Workplace search | `runtime/search/local-resource-search.sqlite` | Stable ID in the selected workplace manifest |
| Workplace accounting | `data/accounting/accounting.sqlite3` | Existing `data/accounting/identity.json` origin ID |

Missing workplace/accounting identity produces a per-target unqualified diagnostic.
Targets must be contained in their selected owner roots and physically distinct.
A changed profile does not relocate a bound database.

## Excluded automatic transitions

There is no automatic arbitrary live rebind, restore over a bound live database,
old-Core rollback after SQL commits, or adoption of unknown remnants. Restore
requires a new destination and a separately controlled offline binding switch;
old-Core rollback requires separately qualified reverse export. Execution abort
is limited to the pre-mutation boundary; committed import/schema work recovers
forward. A new workplace main, full legacy-domain consolidation and other database
drivers are outside this inventory.

## Maintained evidence

The `Storage recovery qualification` workflow runs the migration, identity,
automatic-policy, admission, database, backup, journal and projection suites on
real Windows and Linux. It retains JUnit results and rejects skipped applicable
scenarios. Windows device-name and NTFS junction assertions are explicitly
deselected on Linux. Linux runs real symlink cases; Windows runs real reparse
cases, including the existing junction integration test.

The engine fixtures inject deterministic safety proof; they verify algorithms,
checkpoint atomicity, schema/UUID refusal, WAL/physical source drift and recovery
ordering. They do not authenticate deployment eligibility, complete writer
coverage, or the full Core-update/release transition. The latter still requires
the selected native provider's actual OS evidence.

See [Execution storage and authority](../concepts/execution-storage.md),
[SQLite maintenance](../concepts/sqlite-journal-maintenance.md), and the
[Russian inventory](../ru/audits/issue-17-storage-paths.md).
