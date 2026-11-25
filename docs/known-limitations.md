# Known Limitations

Garage supports local CLI Work without a running service. Forge also supports
a workplace Runtime, a host-owned MCP connection and coordinated workers.

- Session capture depends on the events and message fields the host supplies.
- Native hooks can enforce Forge admission and record supported host events.
  External hook delivery remains bounded by the selected outbox/integration path.
- There is no required daemon or watch-events service.
- Command hook execution is not implemented.
- Process `hooks.subscriptions` entries are declarative/future semantics unless
  a command explicitly implements the action; they do not create handoffs or
  refresh indexes automatically.
- Manual multi-agent assignment/capsule flows, optional shell worker execution
  and explicit agent leases are supported. These do not provide a distributed
  multi-machine scheduler or authorize access beyond the assignment contract.
- A bounded file-first supervisor MVP exists. The optional PF Runtime service
  exists as a local loopback PoC/MVP, including manual background start and
  Windows Task Scheduler autostart. A watch-events service, public network API,
  web UI and database-backed scheduler are not implemented. External workers
  need the executable and configuration declared by their selected driver.
- WTAICC support produces local outbox payloads. Delivery to a remote service requires a separate consumer.
- `--interactive` is a first-run UX marker, not a terminal wizard.
- External documentation mirroring is a plan or stub unless resources are explicitly imported.
- Process Run / Task Batch is file-only. It records runs, tasks, iterations, summaries, events, and outbox payloads, but it does not schedule or execute work in the background.
- Process Authoring creates file-first process packs and companion docs. It does
  not include a process marketplace, visual editor, background scheduler, network
  delivery or automatic migration of already active runs. Process definitions
  remain files; project event/raw-hook journals use SQLite.
- Authoring parity is semantic and file-first. Resource parity records SKIP when a resource kind or id cannot yet be discovered through the current project model.

## Runtime Model

- The CLI runs one command. The workplace app-server (PF Runtime) and the
  host-owned MCP transport have separate lifecycles and memory requirements.
- It does not start background daemons by default.
- The optional PF Runtime service is an explicit workplace lifecycle host, not
  a requirement for default file-first CLI usage.
- Windows autostart is supported only for PF Runtime through a per-user Task
  Scheduler logon task; the stdio MCP server is not a Task Scheduler target.
- The MCP client starts the stdio process from its configuration for each connection.
- Managed Linux `systemd --user` Runtime autostart is not provided.
- On an `organized` workplace, project initialization configures handlers for the
  bundled integration. Garage collection is optional. The client controls activation.
  [Hook support by client](guides/forge-init-hooks.md)
- Hosted MCP behavior depends on the selected agent host supporting stdio MCP.
- TUF metadata and key management are not implemented; update trust is
  based on HTTPS, SHA-256, immutable release assets, and Git provenance.
- `release-test` and smoke commands use per-command process-tree timeouts; a hung child process should fail with command, cwd, timeout, stdout tail, and stderr tail diagnostics instead of hanging silently.
- `release-archive-test --timeout-scale` requires a finite positive value,
  passes that scale to the extracted archive's `release-test`, and separately
  multiplies the outer extracted-test process timeout by the same scale.
- `release-test --trace-smokes` writes per-smoke elapsed and timeout diagnostics
  under `.pf/runtime/release-test/`.
- A long-running watcher is a future optional layer, not part of the core
  runtime.
- External worker execution is opt-in. The built-in [driver registry](concepts/runtime-drivers.md)
  includes manual preparation, external CLI execution and local test workers.
- Shell-launched proof workers write `heartbeat.json` as a required live
  process artifact under `.pf/runtime/agent-runs/<run-id>/<task-id>/`; this
  does not make ProcessForge a background daemon.
- Native subagent dogfooding is external to ProcessForge runtime drivers: a
  host AI environment may launch its own subagents with ProcessForge
  assignment/capsule scope, but ProcessForge does not install or impersonate
  those host agents.
- Native hooks require client-side registration and activation. The available
  events depend on the host and its registered adapter.
- The stored conversation depends on fields delivered by a registered adapter.
  For example, Codex hooks can supply attributed prompts and a final message.
  PF also checks the provenance of managed worker records. Replay can restore
  supported project events. A full streaming transcript requires source messages.
  [Session reads and capture](concepts/session-reads.md)
- Raw ingress rejects canonical payloads larger than 1,048,576 bytes. There is
  no oversized-payload blob spill or receipt yet.
- Project raw/event journals use local SQLite with serialized writers; measured
  local concurrency is not a multi-machine or unbounded-throughput guarantee.
- Future watcher/runner work must stay bounded: streaming reads, offsets or checkpoints, bounded queues, subprocess timeouts, and no full-project in-memory cache by default.
- Platform-specific shell scripts are not required for release validation and are not part of the release surface.

## Requirements Boundary

Use the canonical [requirements](requirements.md) for Python, PyYAML, SQLite,
platform support, optional tools and memory planning. File-only operation does
not require PF Runtime, PowerShell or Git; development and release checks have
additional requirements.
