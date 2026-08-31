# Ограничения

ProcessForge сейчас остается file-first инструментом с bounded orchestration
artifacts.

- File-only mode является поддерживаемым режимом по умолчанию.
- Нет live AI session interception.
- Hooks являются observational и outbox-only.
- Нет обязательного daemon или watch-events service.
- Command hook execution не реализован.
- Process `hooks.subscriptions` entries являются declarative/future semantics,
  если конкретная команда явно не реализует действие; они не создают handoffs и
  не обновляют indexes автоматически.
- Manual multi-agent assignment/capsule flows и optional shell worker execution
  поддерживаются. Multi-agent claim и lease coordination не реализованы.
- Bounded file-first supervisor MVP существует. Optional PF Runtime service
  существует как local loopback PoC/MVP, включая ручной background start и
  Windows Task Scheduler autostart. Watch-events service, public network API,
  web UI, database-backed scheduler и built-in real ecosystem drivers не
  реализованы.
- WTAICC integration не реализована.
- `--interactive` — marker первого запуска, а не terminal wizard.
- External documentation mirroring является планом или stub, пока resources не
  импортированы явно.
- Process Run / Task Batch является file-only. Он записывает runs, tasks,
  iterations, summaries, events и outbox payloads, но не планирует и не
  выполняет work в background.
- Process Authoring создает file-first process packs и companion docs. В него не
  входят process marketplace, visual editor, background scheduler, network
  delivery, database-backed storage или automatic migration уже активных runs.
- Authoring parity является semantic и file-first. Resource parity пишет SKIP,
  когда resource kind или id пока нельзя обнаружить через текущую project model.

## Runtime Model

- ProcessForge core — короткоживущий Python CLI.
- Он не запускает background daemons по умолчанию.
- Optional PF Runtime service является явным workplace lifecycle host, а не
  требованием для default file-first CLI usage.
- Windows autostart поддерживается только для PF Runtime через per-user Task
  Scheduler logon task; stdio MCP server не запускается через Task Scheduler.
- Codex MCP registration является host-owned: Codex запускает stdio MCP process
  из своей конфигурации для fresh host session.
- Managed Linux `systemd --user` Runtime autostart не предоставляется в 1.1.0.
- Codex hooks — optional host-specific telemetry, а не требование generic
  project readiness.
- Hosted MCP зависит от поддержки stdio MCP выбранным agent host.
- TUF metadata и key management не реализованы в 1.1.0; update trust основан на
  HTTPS, SHA-256, immutable release assets и Git provenance.
- `release-test` и smoke commands используют per-command process-tree timeouts;
  зависший child process должен завершиться с diagnostics по command, cwd,
  timeout, stdout tail и stderr tail.
- `release-test --trace-smokes` пишет per-smoke elapsed и timeout diagnostics в
  `.pf/runtime/release-test/`.
- Long-running watcher остается future optional layer, не частью core runtime.
- Runtime driver execution является opt-in. Built-in neutral drivers ограничены
  `manual`, `generic-shell`, `codex-exec`, `test-echo-worker` и
  `test-shell-agent`.
- Shell-launched proof workers пишут `heartbeat.json` как required live process
  artifact в `.pf/runtime/agent-runs/<run-id>/<task-id>/`; это не делает
  ProcessForge background daemon.
- Native subagent dogfooding внешен по отношению к ProcessForge runtime drivers:
  host AI environment может запускать собственных subagents с ProcessForge
  assignment/capsule scope, но ProcessForge не устанавливает и не impersonates
  host agents.
- Codex hook registration является environment-owned: shipped adapter не
  доказывает, что все host hooks зарегистрированы.
- Automatic conversation coverage ограничен attributed `UserPromptSubmit`
  prompts, `Stop.last_assistant_message`, `SubagentStop` final messages и
  PF-owned worker records, когда Codex предоставляет эти поля. Interim streaming
  output и отсутствующие provider fields остаются raw-only или absent.
- Session replay восстанавливает supported normalized Codex-derived project
  events; он не реконструирует полный generic conversation transcript.
- Raw ingress отклоняет canonical payloads больше 1,048,576 bytes. Oversized
  payload blob spill или receipt пока нет.
- Raw indexes являются file-per-event, а recovery может сканировать raw shards;
  scaling improvements требуют измерений и отдельного storage decision.
- Future watcher/runner work должно оставаться bounded: streaming reads, offsets
  или checkpoints, bounded queues, subprocess timeouts и отсутствие full-project
  in-memory cache по умолчанию.
- Platform-specific shell scripts не требуются для release validation и не
  входят в release surface.

## Requirements Boundary

- Для runtime usage рекомендуется Python 3.11+.
- Python 3.10+ допустим только когда текущие tests подтверждают compatibility.
- Runtime usage не требует PowerShell.
- Runtime usage из release archive не требует Git, если не нужна
  version-control integration.
- Development и release checks требуют Python 3.11+, Git, subprocess execution,
  temporary directories и ZIP support из Python standard library.
