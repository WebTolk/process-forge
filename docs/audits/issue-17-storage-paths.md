# Storage paths: implementation and recovery qualification

> Historical evidence. The 2026-11-17 owner decision supersedes the historical-manager/cold-exclusion assumptions and automatic migration described below. Current behavior is specified in [execution storage](../concepts/execution-storage.md) and [journal maintenance](../concepts/sqlite-journal-maintenance.md). Existing owned startup templates are handled by manifest shape, independently of product version.

This finite inventory is maintained with the qualification increment for issue
#17 / T05. Acceptance must identify the exact reviewed revision and OS receipts.
A row describes an implementation boundary, not a qualified deployment or a PASS.
Each path requires its stated ownership and safety evidence.
Neither source tests with injected host proof nor UUID metadata qualify a deployed
old-writer boundary. PF Core maintenance and package lifecycle have different
owners: package updates do not request workplace-wide Core maintenance.

The project flow root is selected explicitly. Its main profile defaults to
`project_main` at `data/pf.sqlite3`; an authorized profile alias must match the
existing execution binding. Project identity comes from the explicit manifest
`project.id`, never a directory name.

| ID | Entry and implemented transition | Authority and recovery |
| --- | --- | --- |
| ST01 | `select_execution_storage`: attach an existing ready main through its exact binding/profile. | Preserve project/store identity. Pending, missing, foreign or conflicting bound storage refuses without JSON fallback. Read access creates no store or identity; SQLite transient sidecars are not domain state. |
| ST02 | `storage_identity_access`: attach a recognized ready events/raw/accounting/search store through its owner slot. | Hold the owner identity gate for the adapter connection. Verify UUID, scope/owner, kind/path and domain schema. Pending and unpinned adopted metadata refuse. |
| ST03 | `migrate-storage.py --apply`, update/first-write coordinator: adopt UUID metadata in place in a recognized legacy database. | Preserve domain IDs, rows, blobs, schema objects and path. Active/unknown safety before pending defers without UUID minting or history scan. Exact selector/plan/pending precede mutation. |
| ST04 | `migrate-storage.py --resume`: recover the exact adoption plan. | Reuse UUID, descriptor, source facts, backup and generation. A metadata commit with a stale file journal rolls forward. Targets commit independently; a later failure does not undo a ready target. |
| ST05 | `journal-maintenance execution-import`, coordinator main import: latest execution snapshots and allocation floors into main SQL. | Require qualified quiescence and old-writer exclusion. Publish pending binding first. Batches are at most 256; import and checkpoint share a transaction. A single ready/sql CAS establishes authority. No invented overwritten history. |
| ST06 | `execution-resume`, coordinator main recovery. | Use exact migration/checksum/evidence selectors and retained backup/checkpoint. Recheck frozen sources and safety before cutover. After ready, SQL remains authority; JSON is only a projection. |
| ST07 | `new_store_identity` plus `add_store_identity`: initialize an explicitly new writable domain target. | Pending precedes creation; metadata shares the domain initialization transaction. Interruption retains the same UUID. Inventory does not create unused absent stores. |
| ST08 | Explicit successful new-flow initialization: fresh main SQL and project journals. | Exclusive creation and native capability are bound by a durable receipt; main/events precede ordinary events. Existing/forced roots are not inferred fresh; recovery retains UUIDs and grants no workplace authority. |
| ST09 | Offline project rename preserves relative SQL attachment; existing prepared attempts retain their original root binding. | The engine fixture injects safety. The physical fresh-project fixture completes a worker, renames the whole directory and verifies main identity, files and accepted report; retry of that bound attempt refuses. This is not successful end-to-end relocation of every store/native binding. |
| ST10 | `journal-maintenance backup/verify/restore`: one SQLite snapshot to a verified bundle and a new absent destination. | Include committed WAL, preserve UUID/data and retain the bundle. Existing/unsafe/tampered destinations refuse. Restore does not switch live binding. Several database snapshots are independent. |
| ST11 | `journal-maintenance inspect/import`, legacy `migrate-hook-journals.py`: recognized events/raw journals to project journal databases. | Preserve IDs/envelopes, originals, quarantine and backups. Operator procedures own writer cutover. Drift/conflicting duplicate refuses even with skip-invalid; interrupted apply retains an incomplete barrier for explicit retry. |
| ST12 | Core archive update: managed replacement, qualified Windows cold handoff, or separate file-only update. | These routes have different prerequisites. Managed publication uses fresh-child maintenance; file-only update supplies no storage-migration authority. Preserve exact selection/epoch and storage UUID/bindings where applicable. Linux primitives do not supply a complete cold-to-managed transition. |

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


## Mandatory readiness and compatibility baseline

New projects must start with current SQL journals/stores. Existing projects must
finish migration and validate identity, schema and readiness before ordinary
mutating Work or worker operations. An unknown/deferred result blocks writes;
old-format readers belong to explicit migration/recovery. Ordinary legacy fallback
is not a supported policy.

[ensure_execution_storage_ready][F] calls the coordinator and then reselects SQL;
a successful-looking report alone is insufficient. [select_execution_storage][C]
can return a legacy route for certain unbound reads. Governed
[adapter_identity_access][AD] now carries write intent through operation host
selection, rejects missing owners and blocked readiness even with `legacy_allowed`,
and requires a validated store identity before writable access. Neither
`automatic=False` nor a journal's `migrating=True` grants migration authority.
Standalone library construction outside a governed operation remains separate.
The [admission test][SA]
`test_ordinary_large_legacy_write_refuses_before_any_history_scan` verifies refusal
without history scanning or appending. The [UUID tests][ID] cover all four adapter
domains and qualified creation/adoption; [configuration tests][CA] cover explicit
and operation-selected hosts without losing governed write identity.

The [lasting contributor rule](../../CONTRIBUTING.md#storage-readiness-and-mandatory-migration)
requires strict SemVer, assessed through users' and agents' published contracts,
without fixing the policy to one release. Small supported project migrations do
not themselves require MAJOR when workflows, public interfaces, integrations and
data/identity guarantees remain compatible. Actual public-contract breaks require
MAJOR even if migration tools exist. Unreleased intermediate fallbacks and tests
are not additional public contracts.

For a genuinely new project, [fresh_project.py][FP] records exclusive flow-root
creation with qualified native capability and pins domain UUIDs before creation.
Main SQL and events are ready before the first onboarding event; project raw/search
initialize lazily with those planned UUIDs. Recovery validates receipt, physical
root, owner and routing; ready missing or foreign stores are not recreated.
Project authority does not extend to workplace stores. [Fresh domain tests][FD]
cover first-event ordering, interruption, UUID preservation, refusals and authority
separation with capability stubs; [fresh-native-SQL][FN] separately tests real lifecycle.

## Criterion-to-source/test matrix

Symbols are relative to the linked file. These are maintained test definitions,
not results of this audit. Engine safety fixtures are synthetic even when SQLite,
files, WAL and subprocesses are real. Required physical evidence remains **pending**
until a result identifies the exact revision, OS/provider, selected cases, outcome
and retained recovery evidence; unavailable required cases are not N/A.

| Path / acceptance criterion | Source anchor | Maintained test anchor(s) and evidence limit |
| --- | --- | --- |
| ST01: exact attach; no fallback for unavailable bound main | [composition.py][C]: `select_execution_storage` | [test_compatibility.py][CP]: `test_pending_binding_missing_db_never_legacy_fallback`, `test_plan_and_binding_identity_tampering_refuses`; [test_configuration_access.py][CA]: `test_bound_storage_never_falls_back_to_projection`. [test_physical_storage_paths.py][PH]: `test_bound_physical_target_refuses_without_fallback` uses sealed CLI with real missing/corrupt/foreign databases, a future format version, schema checksum drift and directory aliases; `test_real_wal_writer_contention_preserves_sql_authority` checks competing SQLite writer refusal and later recovery. |
| ST02: adapter UUID and owner gate through connection lifetime | [storage_migration.py][S]: `storage_identity_access` | [test_storage_uuid.py][ID]: `test_pending_access_blocked_and_ready_access_holds_gate`, `test_adapter_ready_replacement_different_uuid_refuses`; [test_configuration_access.py][CA]: `test_adopted_legacy_access_uses_exact_pin_and_search_keeps_uuid`. Domain coverage does not establish native eligibility. |
| ST03: recognized in-place adoption; exact rows/blobs/schema; refusal before UUID | [storage_migration.py][S]: `_target`, `_apply_target` | [test_storage_uuid.py][ID]: `test_known_formats_in_place_uuid_parity_and_replay`, `test_unknown_or_active_defers_without_uuid_or_maintenance`, `test_unknown_extra_objects_refuse_without_relabel`. Injected proof; deployed writer exclusion pending. |
| ST04: exact selector/UUID/backup reuse, commit-before-journal recovery | [storage_migration.py][S]: `resume`, `_load`, `_repair_ready` | [test_storage_uuid.py][ID]: `test_selector_before_pin_crash_never_remints`, `test_crash_after_commit_or_publication_recovers_exact_uuid`, `test_two_targets_progress_independently`. Fault injection is not physical controller-death proof. |
| ST05: exact snapshot bytes/floors, bounded batches, atomic checkpoint | [execution_migration.py][E]: `_batches`, `_import`, `_cutover` | [test_migration.py][M]: `test_success_exact_bytes_and_one_cutover`, `test_mixed_floor_batches_are_bounded_and_replay_exact`, `test_empty_record_batch_floor_and_checkpoint_rollback_together`. Counts include 257 units; safety remains injected. |
| ST06: deterministic resume; corrupt/drifted evidence refuses; SQL stays authority | [execution_migration.py][E]: `resume`, `_verify`, `_ready` | [test_migration.py][M]: `test_interruption_and_exact_resume`, `test_corrupt_backup_blocks_resume`; [test_compatibility.py][CP]: `test_committed_resume_does_not_reimport_updated_json`. Controlled Windows native interruption cases are described below; deployment-specific qualification remains separate. |
| ST07: new domain pending before creation; same UUID after interruption | [storage_migration.py][S]: `new_store_identity`, `add_store_identity` | [test_storage_uuid.py][ID]: `test_explicit_new_initializer_pins_before_creation_and_commits_metadata`, `test_explicit_initializer_before_creation_retries_same_uuid`. `test_governed_journal_writes_after_qualified_creation_or_migration` verifies ready identity before writes with engine proof; native old-writer exclusion is a separate obligation. |
| ST08: fresh main SQL; pending repair; old-project writes refuse | [composition.py][C]: `_initialize_fresh_execution_storage`, `_repair_fresh_execution_storage`; [first_write.py][F] | [test_automatic.py][A]: `test_fresh_initialization_uses_alias_and_repairs_same_pending_uuid`; [test_required_write_readiness.py][RW]: `test_actual_cli_refuses_unmigrated_project_without_private_paths`, `test_success_report_must_be_followed_by_ready_sql_selection`; [test_fresh_native_sql.py][FN]: `test_fresh_sql_worker_lifecycle_clears_resolved_unknown`. Native backend availability is a prerequisite, not a pass. |
| ST09: offline move without identity/resource loss | [composition.py][C]: relative binding selection; [pf_native_control.py][N]: `ManagedEnrollmentProducer._binding` | [test_migration.py][M]: `test_project_move_preserves_relative_binding_and_identity` covers engine rename. [test_physical_storage_paths.py][PH]: `test_offline_move_preserves_sql_but_refuses_bound_attempt_reuse` checks physical rename, preserved SQL/files/report and refusal of old-attempt reuse. It does not qualify all-store relocation or a fresh post-move native lifecycle. |
| ST10: committed WAL snapshot; UUID-preserving exclusive restore | [backup.py][B]: `SQLiteBackupService.create/verify/restore` | [test_backup.py][BT]: `SQLiteBackupTests.test_wal_commits_are_included_without_changing_source_bytes`, `test_existing_restore_destination_is_preserved`; [test_storage_uuid.py][ID]: `test_backup_restore_of_adopted_store_preserves_uuid`; [test_acceptance.py][IT]: `test_cli_backups_include_committed_wal_and_restore_exclusively`. One database, no live rebind or multi-store atomic snapshot. |
| ST11: journal IDs/envelopes/originals preserved; conflict refusal and incomplete barrier | [journals.py][J]: `JournalMaintenanceService.migrate`, `_flush` | [test_journals.py][JT]: `test_conflicting_source_ids_refuse_before_mutation_even_with_skip`, `test_interrupted_import_keeps_both_barriers_and_retry_does_not_duplicate`, `test_batch_failure_rolls_back_only_current_batch_and_retry_preserves_prior_commit`; [test_acceptance.py][IT]: `test_cli_refusal_quarantine_explicit_skip_replay_and_legacy_entrypoint`. Writer cutover needs separate evidence. |
| ST12: publication/recovery and storage readiness accepted separately | [update.py][U]: `apply_update`; [pf_native_control.py][N]: `replace_core`, `_run_update_child`; [file_update.py][FU] | [test_native_control.py][NT]: `test_joint_real_updater_and_independent_successor_child`, `test_real_updater_retained_target_repair_force_and_authority`; [test_cold_handoff.py][CT]: `test_unqualified_default_refuses_even_synthetic_reset`, `test_g2_interruption_resume_and_corrupt_backup`; [test_file_update.py][FT]: `test_actual_external_sealed_cli_updates_manifest_only_target`, `test_complete_or_partial_managed_markers_never_fall_back`. See provider limits below; installed/source presence is insufficient. |
| All paths: no external file/process/network I/O inside SQL transactions | [execution_migration.py][E]: batches materialized before `_import`; [storage_migration.py][S]: metadata writes separated from backup/journals; [journals.py][J]: bounded rows before `_flush` | [test_storage_admission.py][SA]: `test_migration_application_io_stays_outside_sql_transactions` guards selected Python I/O across six migration routes using actual SQLite transaction state. Admission fixtures remain synthetic; this does not attest native retirement or arbitrary extension I/O. |

## Relocation and Core provider boundaries

ST09 is not a general relocation command or arbitrary rebinding protocol. Relative
storage paths permit the engine fixture's rename, but native
`ManagedEnrollmentProducer._binding` includes an absolute root and physical
device/inode identities. Moving a project does not prove that its selected
installation/owner set remains valid. No full deployed move or automatic repair
of those bindings is established by that test. The physical fixture additionally
shows that [prepared input][PI] records the absolute project root and checks it
on load. Re-preparing the collected attempt after rename returns
`temporary_cleanup_blocked:ValueError`; its immutable input and accepted report
remain preserved. A ready database at the new location does not authorize
rewriting those attempt records.

ST08 has a separate native prerequisite: [supports_owned_execution][N] probes
actual retained process-tree ownership on Windows or Linux. A portable captured
image can support fresh SQL initialization when that probe succeeds; this does
not prove retirement of an old installation's writers.

Verified source entries retain the public inventory in memory; ordinary library
imports remain cold. A source checkout's private `.pf` project data stays mutable
outside that Core image, with alias/hardlink checks. Import and explicit spec
loaders still refuse unpublished code. Sealed images keep their existing private
data boundary. Standard temporary-file staging remains available for private
project data; published code paths still reject custom openers. The source
initialization tests cover both external projects and projects under the
checkout's ignored `.pf/tmp`.

`test_fresh_native_lazy_project_domains_keep_uuid` separately exercises source
and sealed native entries without capability stubs. It creates a standalone
project, lazily initializes raw/search through their ordinary adapters, and
reopens the stores in a second process. Receipt-planned UUIDs, ready pins, event
and raw deduplication, the search file identity and main binding must survive.

`test_migration_application_io_stays_outside_sql_transactions` monitors actual
SQLite transactions for execution import, all four recognized domain adoptions
and journal import. It guards Python file open/scan/fsync, backup, process
creation/wait/signal and network calls, and proves the monitor rejects a write
inside a control transaction. The scanner commits its private deduplication
index before yielding to further source/quarantine I/O or the target importer.
This is bounded transaction evidence with fixture admission, separate from
native old-writer qualification and arbitrary extension-level I/O.

ST12 has three distinct implementation boundaries:

- Managed replacement requires existing qualified enrollment. In
  [pf_native_control.py][N], `LegacyManagedBoundary.__init__` and
  `ManagedEnrollmentProducer.begin_managed_installation` refuse non-Windows;
  `_legacy_closure` returns unknown there. `replace_core` publishes through an
  exclusive lease, then `_run_update_child` independently leases the successor.
  A file publication result does not by itself prove successful storage migration.
- First cold adoption consumes [pf_cold_controller.py][K] `Authority`, not a
  caller flag. `Windows` is Windows-only; `Policy.qualified_versions` defaults
  empty and `retirement` requires qualified exact-build observations.
  [test_cold_handoff.py][CT] gate/boot seams are not positive deployed retirement.
  [pf_linux_cold_controller.py][L] `ControlledCohort` and `FrozenTreeFence`
  implement narrower primitives; they are not wired as the `Authority` consumed
  by `from_cold_provider`. A full Linux cold-to-managed route is unsupported at
  this revision. T05 does not require inventing a new backend; required Linux
  evidence for already-supported paths remains pending when unavailable.
- [file_update.py][FU] `file_update_candidate/apply_file_update` supports a
  separate sealed, unbound installer and a disjoint manifest-owned, never-enrolled
  target. Even partial managed markers refuse fallback. It freezes the archive,
  retains preimages and a truthful failure journal, and uses a cooperating
  updater mutex. Known live service/lock PIDs and failed Windows PID observations
  block before target changes, without contacting a readiness endpoint. A
  successful observation of an absent PID preserves the offline update path.
  It does not enroll a deployment, retire unrelated interpreters,
  or authorize storage migration. `bootstrap_entry` can capture a portable
  file-only image without control/epoch; that is not native exclusion proof.

## Evidence status and completion requirements

The Windows managed recovery cases in [test_native_control.py][NT] add controlled
original-manager evidence: `test_real_legacy_manager_refuses_active_tree_then_retires`
rejects live and detached old writers before handoff;
`test_real_managed_execution_import_process_death_resume` exits a real importer
after a committed 256-unit checkpoint or SQL cutover and resumes independently;
`test_real_managed_uuid_adoption_process_death_resume` exits after metadata commit
and verifies exact resume plus backup/restore across six recognized owner/layout
routes. The import fixture puts actual snapshots on both sides of the checkpoint
and preserves directory-only allocation floors. No synthetic migration safety is
substituted. These tests qualify the declared fixture installation, not the
history of an arbitrary deployment or an unqualified Windows cold-reset build.

[Storage recovery qualification][WF] configures Windows and Linux jobs, retains
JUnit, and rejects skips among selected cases. Linux explicitly deselects the two
Windows-only device-name/junction cases; applicable symlink/reparse cases still
need actual results. The selection includes the migration/UUID/automatic/admission,
database, backup, journal and projection suites, plus physical storage paths,
required-write-readiness, fresh-native-SQL, fresh project domains and configuration
access. Windows also selects the three managed recovery nodes above; Linux has
no corresponding managed provider. Separate update-path jobs select file-only
update tests on both systems, plus Windows managed publication/recovery and
native cold-refusal boundaries. They make no positive cold-reset qualification
claim. [Linux native execution][LW] separately selects fresh-native-SQL
and native lifecycle tests and runs the controlled-cohort suite.
The Linux update job deselects Windows-only `tasklist` fault seams; its native
POSIX live-PID and completed-child controls still run.

Workflow definitions are not execution receipts. The physical suite covers sealed
fresh SQL, bound-target refusal, real writer contention and the existing offline
rename boundary. Acceptance must cite the reviewed revision's Windows/Linux results
and retain useful failures and corrected runs. This increment does not establish
full all-store relocation, arbitrary deployment/cold retirement, or universal
extension-level transaction I/O instrumentation. Exact-source receipts and review
remain required for the controlled managed interruption tests; lower-level or
injected-proof passes do not replace them. A new unsupported relocation or Linux
cold backend is not added here.

See [Execution storage and authority](../concepts/execution-storage.md),
[SQLite maintenance](../concepts/sqlite-journal-maintenance.md), and the
[Russian inventory](../ru/audits/issue-17-storage-paths.md).

[C]: ../../src/processforge_core/executions/composition.py
[F]: ../../src/processforge_core/maintenance/first_write.py
[FP]: ../../src/processforge_core/maintenance/fresh_project.py
[FD]: ../../tests/execution_migration/test_fresh_project_domains.py
[S]: ../../src/processforge_core/maintenance/storage_migration.py
[AD]: ../../src/processforge_core/sqlite_storage.py
[E]: ../../src/processforge_core/maintenance/execution_migration.py
[N]: ../../tools/pf_native_control.py
[B]: ../../src/processforge_core/maintenance/backup.py
[J]: ../../src/processforge_core/maintenance/journals.py
[U]: ../../src/processforge_core/maintenance/update.py
[FU]: ../../src/processforge_core/maintenance/file_update.py
[K]: ../../tools/pf_cold_controller.py
[L]: ../../tools/pf_linux_cold_controller.py
[M]: ../../tests/execution_migration/test_migration.py
[ID]: ../../tests/execution_migration/test_storage_uuid.py
[A]: ../../tests/execution_migration/test_automatic.py
[CP]: ../../tests/execution_migration/test_compatibility.py
[SA]: ../../tests/execution_migration/test_storage_admission.py
[CA]: ../../tests/executions/test_configuration_access.py
[RW]: ../../tests/execution_migration/test_required_write_readiness.py
[FN]: ../../tests/execution_migration/test_fresh_native_sql.py
[PH]: ../../tests/execution_migration/test_physical_storage_paths.py
[PI]: ../../src/processforge_core/prepared/input.py
[NT]: ../../tests/execution_migration/test_native_control.py
[CT]: ../../tests/execution_migration/test_cold_handoff.py
[BT]: ../../tests/maintenance_backup/test_backup.py
[IT]: ../../tests/maintenance_integration/test_acceptance.py
[JT]: ../../tests/maintenance_service/test_journals.py
[FT]: ../../tests/maintenance/test_file_update.py
[WF]: ../../.github/workflows/storage-recovery.yml
[LW]: ../../.github/workflows/linux-native-execution.yml
