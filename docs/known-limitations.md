# Known Limitations

ProcessForge currently runs as a file-first CLI with bounded orchestration
artifacts.

- File-only mode is the supported operating mode.
- There is no live AI session interception.
- Hooks are observational and outbox-only.
- There is no required daemon or watch-events service.
- Command hook execution is not implemented.
- Process `hooks.subscriptions` entries are declarative/future semantics unless
  a command explicitly implements the action; they do not create handoffs or
  refresh indexes automatically.
- Manual multi-agent assignment/capsule flows and optional shell worker
  execution are supported. Multi-agent claim and lease coordination is not
  implemented.
- A bounded file-first supervisor MVP exists. The optional PF Runtime service
  exists as a local loopback PoC/MVP, including manual background start and
  Windows Task Scheduler autostart. A watch-events service, public network API,
  web UI, database-backed scheduler, and built-in real ecosystem drivers are
  not implemented.
- WTAICC integration is not implemented.
- `--interactive` is a first-run UX marker, not a terminal wizard.
- External documentation mirroring is a plan or stub unless resources are explicitly imported.
- Process Run / Task Batch is file-only. It records runs, tasks, iterations, summaries, events, and outbox payloads, but it does not schedule or execute work in the background.
- Process Authoring creates file-first process packs and companion docs. It does not include a process marketplace, visual editor, background scheduler, network delivery, database-backed storage, or automatic migration of already active runs.
- Authoring parity is semantic and file-first. Resource parity records SKIP when a resource kind or id cannot yet be discovered through the current project model.

## Runtime Model

- ProcessForge core is a short-lived Python CLI.
- It does not start background daemons by default.
- The optional PF Runtime service is an explicit workplace lifecycle host, not
  a requirement for default file-first CLI usage.
- Windows autostart is supported only for PF Runtime through a per-user Task
  Scheduler logon task; the stdio MCP server is not a Task Scheduler target.
- Codex MCP registration is host-owned: Codex starts the connected stdio MCP
  process from its configuration for each fresh host session.
- Managed Linux `systemd --user` Runtime autostart is not provided in 1.1.0.
- Codex hooks are optional host-specific telemetry and are not a generic project
  readiness requirement.
- Hosted MCP behavior depends on the selected agent host supporting stdio MCP.
- TUF metadata and key management are not implemented in 1.1.0; update trust is
  based on HTTPS, SHA-256, immutable release assets, and Git provenance.
- `release-test` and smoke commands use per-command process-tree timeouts; a hung child process should fail with command, cwd, timeout, stdout tail, and stderr tail diagnostics instead of hanging silently.
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
- Current automatic conversation coverage is limited to attributed
  `UserPromptSubmit` prompts and PF-owned worker records; generic assistant and
  subagent responses are not captured.
- Session replay repairs supported normalized Codex-derived project events; it
  does not reconstruct a complete generic conversation transcript.
- Raw ingress rejects canonical payloads larger than 1,048,576 bytes. There is
  no oversized-payload blob spill or receipt yet.
- Raw indexes are file-per-event and recovery may scan raw shards; scaling
  improvements require measurement and a separate storage decision.
- Future watcher/runner work must stay bounded: streaming reads, offsets or checkpoints, bounded queues, subprocess timeouts, and no full-project in-memory cache by default.
- Platform-specific shell scripts are not required for release validation and are not part of the release surface.

## Requirements Boundary

- Python 3.11+ is recommended for runtime usage.
- Python 3.10+ is allowed only when the current tests confirm compatibility.
- Runtime usage does not require PowerShell.
- Runtime usage from a release archive does not require Git unless version-control integration is wanted.
- Development and release checks require Python 3.11+, Git, subprocess execution, temporary directories, and Python standard-library ZIP support.
