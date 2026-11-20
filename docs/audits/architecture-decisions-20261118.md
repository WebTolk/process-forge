# Architecture decision reconciliation, November 18, 2026

[Русская версия](../ru/audits/architecture-decisions-20261118.md)

The [decision register](../architecture/README.md) preserves the identifiers
D01–D22 and H01 from the October architecture review. The November comparison
examined GitHub `dev` through
[`8e8959de`](https://github.com/WebTolk/process-forge/commit/8e8959defb340fb3157e9cfd880d0b2e7ca64498).
This publication rechecked the relevant source and public contracts through
[`a03f7b77`](https://github.com/WebTolk/process-forge/commit/a03f7b772e156624b59cb593b8bdd2aca7637940),
including the subsequent
[release checklist update](https://github.com/WebTolk/process-forge/pull/88)
and [archive failure evidence update](https://github.com/WebTolk/process-forge/pull/89).

## Decisions and operating assumptions that changed

### D17, D19 and D20 — Explicit offline journal migration

The October R02 design combined UUID and data preservation with automatic
native migration and a one-time first cold handoff for historical installations
without a proven writer owner. The November 17 owner decision removed the
historical-manager and cold-controller route. Project initialization now
prepares current SQL journals for new projects. Existing projects use explicit
offline journal migration. Ordinary Work and worker writes require journal
readiness and report `storage_migration_required` where migration is needed.
Ordinary writes require a validated SQL store. A pending cutover, invalid
binding or unavailable store blocks those writes. The documented recovery
path follows the recorded state. Reads and recovery of existing attempts keep
their documented boundaries.
[Decision and historical evidence](issue-17-storage-paths.md),
[PR #56](https://github.com/WebTolk/process-forge/pull/56),
[PR #69](https://github.com/WebTolk/process-forge/pull/69)

The migration still validates the selected store, preserves UUIDs and source
data, and retains a backup and checkpoint for recovery. The
`tools/migrate-storage.py` entry supports `--inspect`, `--apply` and `--resume`.
Apply and resume require `--offline-confirmed`, which records responsibility for
stopping historical writers. The Garage operator or Forge updater takes that
responsibility. Local admission checks cover the selected routes and owners,
including a known Runtime. Native leases cover controlled startup and shutdown
of owned processes. Recovery reuses the pinned plan, source and UUID.
Validated receipt pairs preserve the collection state of historical attempts.
[Execution storage](../concepts/execution-storage.md#explicit-migration-and-update-responsibility),
[journal maintenance](../concepts/sqlite-journal-maintenance.md),
[PR #70](https://github.com/WebTolk/process-forge/pull/70)

### D03 — Worker MCP declarations

Earlier prepared-input documents described MCP as a resource whose grant was
resolved and checked during preparation. Worker preparation now records
`input.resources.requested.mcp` as declarations and leaves
`input.resources.grants.mcp` empty. The coding agent manages its connections and
approvals. PF continues to enforce the Work capsule and the file, knowledge,
template and tool permissions defined by the prepared execution contract.
[Work context](../concepts/work-context.md),
[PR #57](https://github.com/WebTolk/process-forge/pull/57)

### D01, D07 and D10 — MCP backend ownership

The earlier description assumed that host-owned stdio retained the loaded Core.
The current host-owned bridge keeps the stdio connection and chooses the backend
according to the coordination mode. Garage starts a Core child for a backend
request. Forge sends requests to the existing authenticated loopback Runtime
and checks its instance identity. A Forge backend failure returns a backend
error. A client still using the old entry process needs to start the new bridge
once. Subsequent compatible Core updates use the backend selected for each
request. [MCP updates](../concepts/mcp-updates.md),
[PR #50](https://github.com/WebTolk/process-forge/pull/50),
[PR #74](https://github.com/WebTolk/process-forge/pull/74)

### D01, D10 and D19 — Explicit Runtime management during Core update

The external file updater now offers an explicit `--manage-runtime` mode for
Forge. It preflights the verified archive, stops the existing Runtime through
its guarded stop path, replaces the files while holding the startup mutex and
starts the Runtime from the target Core. It checks the loaded target build and
process identity. Project data migration remains a separate maintenance action.
The file-only update path and before-manifest recovery have their own guards.
[Core update manifest](../concepts/core-update-manifest.md),
[PR #62](https://github.com/WebTolk/process-forge/pull/62),
[PR #71](https://github.com/WebTolk/process-forge/pull/71),
[PR #75](https://github.com/WebTolk/process-forge/pull/75)

### H01, D06 and D21 — Historical scope

The prerelease compatibility exception H01 applied before public contracts
existed. The current contribution policy assesses user-facing behavior, data
and identity under SemVer. An explicit storage migration is compatible when
supported workflows, public interfaces and data and identity guarantees are
preserved. The early D06 framework proposal and the D21 alpha6 stop condition
belong to their documented stages. D07 and D08 describe service ownership for
current refactoring. Source, archive, installed Core, Runtime and connected
client remain distinct verification layers.
[Compatibility policy](../../CONTRIBUTING.md#storage-readiness-and-mandatory-migration),
[PR #58](https://github.com/WebTolk/process-forge/pull/58),
[release checklist](../release-checklist.md)

## Implementation changes within the decisions

- **D09 and D11, journals and current activity.** Runtime and recovery read
  events from the configured journal owner. Pending hook deliveries are read
  in the event admission transaction. Delivery is performed after it. These
  changes keep current operations on bounded reads and preserve the journal's
  required facts. [PR #64](https://github.com/WebTolk/process-forge/pull/64),
  [PR #86](https://github.com/WebTolk/process-forge/pull/86),
  [PR #87](https://github.com/WebTolk/process-forge/pull/87)
- **D13 and D14, first Workplace Search build.** Garage can explicitly build
  the derived Workplace FTS5 index against the selected Workplace identity
  and path. Pending initialization retains the UUID across recovery.
  Context and query paths continue to consume the existing index.
  [Search index](../concepts/resource-search-index.md),
  [PR #84](https://github.com/WebTolk/process-forge/pull/84)
- **D11 and D19, Linux execution.** Linux adds native ownership with user and
  PID namespaces and pidfd. Admission and drain depend on supported host
  capabilities and proof of ownership. PR #69 removed the experimental Linux
  cold controller from PRs #51 and #52. Ordinary owned-worker execution and
  its guards remain. [Linux owned execution](../concepts/linux-owned-execution.md),
  [PR #27](https://github.com/WebTolk/process-forge/pull/27),
  [PR #69](https://github.com/WebTolk/process-forge/pull/69)
- **D03 and D11, completion and historical collection.** Work completion
  requires a terminal outcome. Intent validation precedes replay writes.
  Historical collection checks the pinned output and receipt against the
  relevant attempt. [PR #41](https://github.com/WebTolk/process-forge/pull/41),
  [PR #42](https://github.com/WebTolk/process-forge/pull/42),
  [PR #44](https://github.com/WebTolk/process-forge/pull/44),
  [PR #46](https://github.com/WebTolk/process-forge/pull/46)
- **D04 and D21, public source boundary.** A fresh source clone uses the public
  instructions and shipped checks. The root `.pf/` contains the repository's
  private local state. Public release checks run from the source and archive.
  A local dogfooding suite has its own evidence. [Contributor guide](../../CONTRIBUTING.md),
  [PR #7](https://github.com/WebTolk/process-forge/pull/7),
  [PR #88](https://github.com/WebTolk/process-forge/pull/88)

## Open findings at the reviewed revision

| Area | Evidence and reading guidance |
| --- | --- |
| Journal migration documentation | The original R02 section still uses full host exclusion in its description. The current offline procedure is in the later operator/updater migration section and implements the November decision. [Historical section](https://github.com/WebTolk/process-forge/blob/a03f7b772e156624b59cb593b8bdd2aca7637940/docs/concepts/sqlite-journal-maintenance.md#L160-L176), [current procedure](../concepts/execution-storage.md#explicit-migration-and-update-responsibility) |
| Prepared Input documentation | Both languages still describe preflight MCP grants. Read that wording with the revised worker MCP declaration rule in Work Context. [Prepared Input](../concepts/prepared-input.md), [Work Context](../concepts/work-context.md) |
| Search documentation | The general index concept covers the derived index. The first Workplace build and its recovery are implemented in the scoped maintenance path. [Implementation](https://github.com/WebTolk/process-forge/blob/a03f7b772e156624b59cb593b8bdd2aca7637940/src/processforge_core/maintenance/fresh_workplace.py#L21-L62) |
| Core ownership, D08 | `ProcessExecutionService` still calls `validate_assignment_scope_overlaps` in the procedural monolith. The remaining rule is a concrete example of an incomplete service extraction. [Service call](https://github.com/WebTolk/process-forge/blob/a03f7b772e156624b59cb593b8bdd2aca7637940/src/processforge_core/process_execution.py#L637), [rule implementation](https://github.com/WebTolk/process-forge/blob/a03f7b772e156624b59cb593b8bdd2aca7637940/tools/processforge.py#L6455) |

This report is a static comparison at the named source revision. The
400,000-launch criterion belongs to focused performance verification. Archive
qualification, target installation and the behavior of an actual connected
client each require evidence for the corresponding candidate and environment.
[Release checklist](../release-checklist.md)
