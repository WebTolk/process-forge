# Модель среды выполнения

![Lifecycle run/task/iteration](../../assets/processforge-run-lifecycle.svg)

По умолчанию ProcessForge использует короткоживущие CLI-команды. Команда читает
project и workplace files, пишет нужный artifact или runtime record и
завершается. Optional Runtime host и MCP facade являются адаптерами вокруг
общего Python Core; `tools/processforge.py` остается legacy CLI-adapter
boundary.

File layout является runtime contract:

- `.pf/process-forge.yaml` хранит project manifest.
- `.pf/contexts/` хранит refreshed context snapshots.
- `.pf/runs/` хранит run records.
- `.pf/assignments/` хранит task и iteration records.
- `.pf/artifacts/`, `.pf/reviews/` и `.pf/handoffs/` хранят evidence и delivery material.
- `.pf/runtime/events/events.sqlite3` хранит необязательную историю и необходимые ID и факты проверки.
- `.pf/runtime/agent-events/hooks.sqlite3` хранит квитанции хуков, незавершённую обработку и необязательные сырые данные.
- `.pf/runtime/agent-runs/` хранит optional worker process state.
- `.pf/runtime/supervisor/` хранит optional supervisor loop state.

## Приём хуков проекта

После проверки проекта исходные данные хука фиксируются в его приватном
журнале `.pf/runtime/agent-events/hooks.sqlite3`. История нормализованных событий
хранится отдельно в `events.sqlite3`. Agent Ledger и служебное состояние Runtime
остаются общими для рабочей среды.

Обработчик хука больше не пересобирает историю команд и представления стадий.
История пересобирается явной командой; представление стадий обновляется при
изменении входных файлов или последних фактов проверки. При неизменных данных
очередной такт не разбирает YAML задач и не вычисляет заново хеши результатов.
Проверки Work продолжают проверять актуальные исходные данные. Порядок переноса
описан в [SQLite и миграции журналов](../../concepts/hook-journal-sqlite.md).

Release archive включает `src/processforge_core`, `tools/processforge.py` и
`tools/pf_runtime/*`, но не включает workplace raw journals, chat transcripts,
quarantine data, event indexes или replay checkpoints.

Core CLI runtime не требует daemon. Optional Runtime Host helpers могут
запускаться как короткие file-first ticks, а optional PF Runtime service может
работать как long-lived workplace process, если его явно запустили или
установили Windows autostart.

Runtime drivers и process supervisor являются optional runtime helpers. См.
[Runtime drivers](runtime-drivers.md) и [Process supervisor](process-supervisor.md).

## Distribution Root Versus Linked Project

Из корня дистрибутива:

```bash
python bin/pf.py release-test --root .
```

Внутри подключенного проекта:

```bash
python .pf/runtime/bin/pf.py doctor-project --project-root .
```

## Runtime Requirements

Для runtime usage рекомендуется Python 3.11+. Python 3.10+ допустим только
когда текущие tests подтверждают compatibility. Также нужны зависимости из
`requirements.txt`, включая `PyYAML`, UTF-8 capable filesystem и read/write
access к ProcessForge distribution, workplace и project folders.

Default Runtime usage не требует PowerShell, Git, daemon или background process.
Git нужен только для version-control integration или development/release checks.
Optional PF Runtime service startup описан в
[Автозапуск Runtime и запуск Codex MCP](../getting-started/runtime-autostart.md).

## Runtime, Ledger и MCP interfaces

PF Runtime — workplace-scoped local lifecycle host, scheduler и IPC transport.
Это не второй PF Core. Agent Ledger владеет canonical session-to-project
binding; project и session maps Runtime являются только rebuildable caches.

Поле `scheduler_alive` показывает, работает ли поток планировщика. Ошибка
операции планировщика или повреждение кеша маршрутизации переводит состояние здоровья в
`degraded`; остальные доступные проекты продолжают обрабатываться. После
успешной проверки состояние восстанавливается. Остановка планировщика видна
даже при сохранении состояния IPC `ready`.
Неуспешные попытки исполнителей и требования восстановления сбора остаются
результатами задач. Они видны в `inspector_result` каждого проекта внутри
`last_scheduler_result` и не переводят исправную службу в `degraded`.
Команды `supervisor tick` и Runtime-host tick сохраняют ненулевой код возврата
и статус неуспеха при таких результатах. Runtime-host tick дополнительно
возвращает `scheduler_status` для оценки исправности службы. Повторного обхода
данных или принятия заблокированного результата при этом нет. Успешная публикация
метрик считается выполненной операцией и при частичном покрытии: неизвестные
значения, нижние границы счётчиков и причины неполноты остаются явно указаны.
Захват блокировки запрещён, если её владелец жив или его состояние нельзя
надёжно проверить, в том числе при отсутствии или повреждении lock-файла.
Запись завершившегося процесса допускает восстановление; наличие живого PID
само по себе не доказывает, что неполная запись устарела.

Routed session восстанавливается из Ledger record `project_id` и `project_root`.
Request или event с другим project отклоняется. Это сохраняет recovery после
удаления Runtime cache и cross-project isolation независимо от daemon.

Codex hooks — тонкие fact adapters. Они нормализуют documented lifecycle или
tool facts, добавляют existing PF events и делегируют check-in, heartbeat и
checkout в Core. Stdio MCP facade в основном bounded/read-oriented, но также
предоставляет governed mutation tools для project initialization, repair и work
bootstrap. Эти mutating tools ограничены и требуют guard inputs, например
`apply: true`.

Stdio MCP process принадлежит MCP host, а не PF Runtime autostart. Codex
запускает его из host MCP configuration для каждой connected session. См.
[PF Runtime MCP facade](runtime-mcp.md) и
[Автозапуск Runtime и запуск Codex MCP](../getting-started/runtime-autostart.md).

## Декларативные технические проекции

Process definition может объявить у stage `technical_obligations`. Runtime Host
читает эту декларацию и пишет только отдельный generated file в
`.pf/artifacts/projections/`; он не содержит stage business rules и не
редактирует semantic reports, handoffs или output bodies.

Первый projector, `required-output-readiness`, привязан к stage `collect`
процесса `process-supervisor`. Он выводит текущую stage obligation из
assignment, Inspector worker state и required-output fingerprints. View может
быть `current`, `stale`, `missing` или `invalid`. Его можно пересобрать через
`runtime-host rebuild-projections` и проверить без daemon через
`runtime-host projection-doctor`.
