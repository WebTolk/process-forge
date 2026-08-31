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
- `.pf/runtime/events/events.ndjson` хранит event envelopes.
- `.pf/runtime/agent-runs/` хранит optional worker process state.
- `.pf/runtime/supervisor/` хранит optional supervisor loop state.

## Workplace raw ingress

Agent-native payloads сначала пишутся в приватный workplace Raw Event Journal
`<workplace>/runtime/agent-events/`, а не напрямую в project event file. Там
хранятся raw shards, dedupe/index state, quarantine и replay checkpoints. Agent
Ledger и Runtime service state/logs также являются workplace-scoped. Project
records остаются локальными для `.pf/runtime/`.

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
