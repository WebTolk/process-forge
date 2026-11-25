# Ограничения

В Garage можно вести Work через локальный CLI без фоновой службы. В Forge
также доступны Runtime рабочего места, подключение MCP и координация исполнителей.

- Захват переписки зависит от событий и полей, переданных хостом.
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
  web UI и database-backed scheduler не реализованы. Для внешнего исполнителя
  нужны программа и настройки, предусмотренные выбранным драйвером.
- Для WTAICC ядро формирует локальные файлы outbox. Для доставки в удалённую службу нужен отдельный потребитель.
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

- CLI выполняет одну команду. У app-server рабочего места (PF Runtime) и
  stdio-транспорта MCP свои жизненные циклы и требования к памяти.
- Он не запускает background daemons по умолчанию.
- Optional PF Runtime service является явным workplace lifecycle host, а не
  требованием для default file-first CLI usage.
- Windows autostart поддерживается только для PF Runtime через per-user Task
  Scheduler logon task; stdio MCP server не запускается через Task Scheduler.
- При каждом соединении MCP-клиент запускает stdio-процесс из своей конфигурации.
- Managed Linux `systemd --user` Runtime autostart не предоставляется.
- В рабочем месте с режимом `organized` при инициализации проекта настраиваются
  обработчики штатной интеграции. В Garage сбор событий необязателен. Активацией
  управляет клиент. [Поддержка хуков](guides/forge-init-hooks.md)
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
- Внешних исполнителей запускают по выбору оператора. В штатном
  [реестре драйверов](concepts/runtime-drivers.md) есть ручная подготовка,
  запуск внешнего CLI и локальные исполнители для проверок.
- Shell-launched proof workers пишут `heartbeat.json` как required live process
  artifact в `.pf/runtime/agent-runs/<run-id>/<task-id>/`; это не делает
  ProcessForge background daemon.
- Native subagent dogfooding внешен по отношению к ProcessForge runtime drivers:
  host AI environment может запускать собственных subagents с ProcessForge
  assignment/capsule scope, но ProcessForge не устанавливает и не impersonates
  host agents.
- Хуки регистрируются и активируются в клиенте. Доступные события зависят от
  клиента и его зарегистрированного адаптера.
- Содержимое переписки зависит от полей зарегистрированного адаптера. Например,
  хуки Codex могут передать запрос пользователя и финальный ответ. PF также
  проверяет происхождение записей своих исполнителей. Повторная обработка
  восстанавливает поддерживаемые события. Для полной переписки нужны исходные
  сообщения. [Чтение данных сессии](concepts/session-reads.md)
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
