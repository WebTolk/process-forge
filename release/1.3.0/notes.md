# ProcessForge 1.3.0

## Changes since 1.2.0

- New projects use SQLite for worker execution state and journals. Indexed
  queries read current executions, and migration preserves the original
  records and the latest observed attempt.
- In Forge, the selected Workplace Runtime handles MCP requests, CLI Work
  commands and continuations with explicit Work selectors. The CLI reports
  `forge_runtime_unavailable` when it cannot reach Runtime. MCP clients can
  reconnect after a compatible Core update or Runtime restart. Garage runs
  these commands locally.
- The updater verifies the release payload and preserves project and Workplace
  data. It can manage Runtime during replacement and resume an interrupted
  file update from its recorded state.
- Native Windows and Linux worker handling checks process ownership. Collected
  results are retained when their completion and collection records match.
- The distribution includes the [architecture decisions](../../docs/architecture/README.md)
  and updated operator guidance in English and Russian.

## Update from 1.2.0

Back up the Project and Workplace before replacing Core. Run the verified
updater from a directory outside the installed Core. Forge can use
`--manage-runtime` for the managed Runtime. Stop other writers, including
direct `worker-run` and legacy Run/Task operations, during maintenance.
[Core update and recovery](../../docs/concepts/update-lifecycle.md)

If an existing Project returns `storage_migration_required`, run the explicit
storage migration with Runtime and other writers offline. Known 1.2.0 worker
heartbeats are preserved byte for byte, including when the latest attempt is
prepared and has yet to run. The migration retains backups and checkpoints for
resume. [Journal and execution migration](../../docs/concepts/sqlite-journal-maintenance.md)
