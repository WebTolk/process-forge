# ProcessForge 1.3.0-beta4

Beta4 packages the Core changes through the 18 November architecture review.
It adds native worker ownership on supported Linux hosts and initializes new
projects with SQLite execution and event storage. Existing Work, assignments
and context capsules retain their identities during supported migration.

## Upgrading an existing installation

Run the verified updater from a directory outside the installed Core. In
Garage, stop PF and other writers before applying updates or migrating storage.
In Forge, the external updater can stop its managed Runtime, replace Core files
and restart the Runtime with `--manage-runtime`. Direct CLI Work commands can
still execute locally. Stop those writers as part of the maintenance window.

Use the explicit storage migration procedure when ordinary writes report
`storage_migration_required`. Migration preserves source bytes, checkpoints
and backups. After SQL cutover, recovery uses the retained data and migration
records. [Storage migration guide](../../docs/concepts/sqlite-journal-maintenance.md)

## Changes in this checkpoint

- Forge MCP sessions route through Runtime and reconnect after its restart.
  Event admission and pending delivery share a transaction. Delivery runs
  after commit.
- Current execution checks use the current state index as history grows.
  Worker recovery retains ownership and previously completed collections.
- The file updater handles an owned file becoming a directory and preserves
  the observed preimage for recovery. Windows protects agent-entry journals
  and cleanup receipts before writing their contents.
- The distribution includes the English and Russian architecture decision
  register. [Architecture decisions](../../docs/architecture/README.md)

The stable update channel continues to offer 1.2.0. Beta4 is available from
the prerelease assets.
