# Ограничения

ProcessForge сейчас остается file-first инструментом с bounded orchestration
artifacts.

- File-only mode является поддерживаемым режимом по умолчанию.
- Нет live AI session interception.
- Нативные хуки могут проверять допуск Forge и записывать поддерживаемые события
  host. Внешняя доставка ограничена выбранным механизмом outbox или интеграции.
- Нет обязательного daemon или watch-events service.
- Command hook execution не реализован.
- Process `hooks.subscriptions` entries являются declarative/future semantics,
  если конкретная команда явно не реализует действие; они не создают handoffs и
  не обновляют indexes автоматически.
- Manual multi-agent assignment/capsule flows и optional shell worker execution
  поддерживаются вместе с явными agent leases. Это не распределённый планировщик
  нескольких машин и не расширение прав за пределы assignment contract.
- Bounded file-first supervisor MVP существует. Optional PF Runtime service
  существует как local loopback PoC/MVP, включая ручной background start и
  Windows Task Scheduler autostart. Watch-events service, public network API,
  web UI и database-backed scheduler не реализованы. Поставляемый драйвер
  `codex-exec` требует отдельно доступного Codex CLI и настройки host.
- WTAICC integration не реализована.
- `--interactive` — marker первого запуска, а не terminal wizard.
- External documentation mirroring является планом или stub, пока resources не
  импортированы явно.
- Process Run / Task Batch является file-only. Он записывает runs, tasks,
  iterations, summaries, events и outbox payloads, но не планирует и не
  выполняет work в background.
- Process Authoring создает file-first process packs и companion docs. В него не
  входят process marketplace, visual editor, background scheduler, network
  delivery или automatic migration уже активных runs. Определения процессов
  остаются файлами; журналы событий проекта и raw hooks используют SQLite.
- Authoring parity является semantic и file-first. Resource parity пишет SKIP,
  когда resource kind или id пока нельзя обнаружить через текущую project model.

## Runtime Model

- Python CLI служит входом для файлового режима. Необязательные долгоживущие
  app-server, MCP и Runtime имеют отдельные жизненные циклы и требования к памяти.
- Он не запускает background daemons по умолчанию.
- Optional PF Runtime service является явным workplace lifecycle host, а не
  требованием для default file-first CLI usage.
- Windows autostart поддерживается только для PF Runtime через per-user Task
  Scheduler logon task; stdio MCP server не запускается через Task Scheduler.
- Codex MCP registration является host-owned: Codex запускает stdio MCP process
  из своей конфигурации для fresh host session.
- Managed Linux `systemd --user` Runtime autostart не предоставляется.
- Codex hooks — optional host-specific telemetry, а не требование generic
  project readiness.
- Hosted MCP зависит от поддержки stdio MCP выбранным agent host.
- TUF metadata и key management не реализованы; update trust основан на
  HTTPS, SHA-256, immutable release assets и Git provenance.
- `release-test` и smoke commands используют per-command process-tree timeouts;
  зависший child process должен завершиться с diagnostics по command, cwd,
  timeout, stdout tail и stderr tail.
- `release-archive-test --timeout-scale` требует finite positive значение,
  передаёт этот scale во вложенный `release-test` извлечённого архива и отдельно
  умножает внешний process timeout extracted-test на тот же scale.
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
- Автоматический сбор переписки включает атрибутированные `UserPromptSubmit`,
  финальные сообщения из `Stop`, `SubagentStop` или `SessionEnd` и записи
  исполнителей PF. Он зависит от полей provider, например
  `last_assistant_message`; промежуточный потоковый вывод не даёт полной переписки.
- Session replay восстанавливает supported normalized Codex-derived project
  events; он не реконструирует полный generic conversation transcript.
- Raw ingress отклоняет canonical payloads больше 1,048,576 bytes. Oversized
  payload blob spill или receipt пока нет.
- Журналы проекта используют локальную SQLite с последовательной записью;
  проверки локальной конкуренции не гарантируют работу нескольких машин или
  неограниченную пропускную способность.
- Future watcher/runner work должно оставаться bounded: streaming reads, offsets
  или checkpoints, bounded queues, subprocess timeouts и отсутствие full-project
  in-memory cache по умолчанию.
- Platform-specific shell scripts не требуются для release validation и не
  входят в release surface.

## Requirements Boundary

Проверяйте Python, PyYAML, SQLite, поддержку ОС, необязательные инструменты
и планирование памяти по единому разделу [требований](requirements.md).
Файловый режим не требует PF Runtime, PowerShell или Git; проверки разработки
и релиза предъявляют дополнительные требования.
