# Known Limitations

ProcessForge currently runs as a file-first CLI with bounded orchestration
artifacts.

- File-only mode is the supported operating mode.
- There is no live AI session interception.
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
  web UI and database-backed scheduler are not implemented. The shipped
  `codex-exec` driver requires a separately available Codex CLI and host setup.
- WTAICC integration is not implemented.
- `--interactive` is a first-run UX marker, not a terminal wizard.
- External documentation mirroring is a plan or stub unless resources are explicitly imported.
- Process Run / Task Batch is file-only. It records runs, tasks, iterations, summaries, events, and outbox payloads, but it does not schedule or execute work in the background.
- Process Authoring creates file-first process packs and companion docs. It does
  not include a process marketplace, visual editor, background scheduler, network
  delivery or automatic migration of already active runs. Process definitions
  remain files; project event/raw-hook journals use SQLite.
- Authoring parity is semantic and file-first. Resource parity records SKIP when a resource kind or id cannot yet be discovered through the current project model.

## Runtime Model

- The Python CLI is the file-only entry point. Optional long-lived app-server,
  MCP and Runtime processes have separate lifecycles and memory requirements.
- It does not start background daemons by default.
- The optional PF Runtime service is an explicit workplace lifecycle host, not
  a requirement for default file-first CLI usage.
- Windows autostart is supported only for PF Runtime through a per-user Task
  Scheduler logon task; the stdio MCP server is not a Task Scheduler target.
- Codex MCP registration is host-owned: Codex starts the connected stdio MCP
  process from its configuration for each fresh host session.
- Managed Linux `systemd --user` Runtime autostart is not provided.
- Codex hooks are optional host-specific telemetry and are not a generic project
  readiness requirement.
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
- Runtime driver execution is opt-in. Built-in neutral drivers are limited to
  `manual`, `generic-shell`, `codex-exec`, `test-echo-worker`, and
  `test-shell-agent`.
- Shell-launched proof workers write `heartbeat.json` as a required live
  process artifact under `.pf/runtime/agent-runs/<run-id>/<task-id>/`; this
  does not make ProcessForge a background daemon.
- Native subagent dogfooding is external to ProcessForge runtime drivers: a
  host AI environment may launch its own subagents with ProcessForge
  assignment/capsule scope, but ProcessForge does not install or impersonate
  those host agents.
- Codex hook registration is environment-owned: the shipped adapter does not
  prove that all host hooks are registered.
- Current automatic conversation coverage includes attributed `UserPromptSubmit`
  prompts, final messages supplied in `Stop`, `SubagentStop` or `SessionEnd`
  payloads, and PF-owned worker records. It depends on provider fields such as
  `last_assistant_message`; interim streaming output is not a complete transcript.
- Session replay repairs supported normalized Codex-derived project events; it
  does not reconstruct a complete generic conversation transcript.
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
