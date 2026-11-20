# ProcessForge 1.3.0

You can now send the built-in Codex worker into an ordinary project folder. There is no need to create a Git repository just to run a task. We tested the whole path on Windows and Linux, from assigning the work to collecting its result.

## Day-to-day changes

- **Resume interrupted work.** On Windows and Linux, ProcessForge checks which processes belong to the worker. If a result has already been accepted, collecting it again returns that result. New projects keep an index of current executions so PF can find them without going through every finished attempt.
- **Reconnect an agent to Forge.** An MCP client can reconnect after the service restarts or the Core receives a compatible update. Commands report when the service is unavailable. Garage still supports local task work.
- **Continue an interrupted update.** The updater verifies files and keeps backup copies. We tested an upgrade from the public 1.2.0 release and seven recovery scenarios on each operating system. [1.2.0 upgrade checks](https://github.com/WebTolk/process-forge/issues/19)

## Before and after

We gave both versions the same 258 saved run records on one Windows computer. Both found the same 15 active runs in the same order.

| Find active runs | 1.2.0 | 1.3.0 |
| --- | ---: | ---: |
| First lookup in a new process | 987 ms | 959 ms |
| Repeat lookup | 55 ms | 53 ms |

The figures are medians of seven first lookups and fourteen repeats per version. The difference on repeat lookups was small on this project.

Concurrent connections showed a larger change during 1.3.0 development. On Windows, six clients registered twelve sessions across two projects. The slowest registration took **2.95 s before the fix**, then **1.47 s and 1.72 s** in two runs after it. All twelve sessions resolved to their projects. [Registration measurements](https://github.com/WebTolk/process-forge/pull/87)

An October test used 570 records. After warm-up, finding the same 49 active runs took **3.44–4.55 s of CPU time before the fix and 0.141 s after it**. Users already received that improvement in 1.2.0. [October change](https://github.com/WebTolk/process-forge/commit/8f00ca1711f1d7ad276da61a9fcbec907da0cd36)

## Upgrading from 1.2.0

Back up the project and Workplace. Let workers finish and stop other processes writing to the project. Run the verified updater from outside the installed Core directory. Forge users can pass `--manage-runtime` to let the updater stop and restart the service. Installation requires your confirmation. [Core update and recovery](../../docs/concepts/update-lifecycle.md)

New projects start with SQLite storage. If an existing project reports `storage_migration_required` on a write, stop the service and follow the migration guide. You can resume an interrupted migration from its checkpoint. If PF cannot establish the state of an old worker, an operator needs to check it. [Migrate project history and execution state](../../docs/concepts/sqlite-journal-maintenance.md)

Native Linux workers require permission to create user and PID namespaces, readable procfs, and Python 3.11+ with pidfd support. Check these settings if you run PF in a container. [Linux worker requirements](../../docs/concepts/linux-owned-execution.md)
