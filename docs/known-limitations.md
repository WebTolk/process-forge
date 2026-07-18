# Known Limitations

ProcessForge v0.1 is a file-first, single-agent release candidate.

- File-only mode is the supported operating mode.
- There is no live AI session interception.
- Hooks are observational and outbox-only.
- There is no daemon or watch-events service.
- Command hook execution is not implemented.
- Multi-agent claim and lease coordination is not implemented.
- Runner and supervisor services are not implemented.
- WTAICC integration is not implemented.
- `--interactive` is a first-run UX marker, not a terminal wizard.
- External documentation mirroring is a plan or stub unless resources are explicitly imported.
- Process Run / Task Batch MVP is file-only. It records runs, tasks, iterations, summaries, events, and outbox payloads, but it does not schedule or execute work in the background.

## Runtime Model

- ProcessForge v0.1 core is a short-lived Python CLI.
- It does not start background daemons by default.
- A long-running watcher or runner is a future optional layer, not part of the v0.1 core.
- Future watcher/runner work must stay bounded: streaming reads, offsets or checkpoints, bounded queues, subprocess timeouts, and no full-project in-memory cache by default.
