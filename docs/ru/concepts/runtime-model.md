# Модель среды выполнения

![Lifecycle run/task/iteration](../../assets/processforge-run-lifecycle.svg)

ProcessForge работает через короткие CLI-команды. Команда читает файлы workplace
и project, записывает нужный артефакт или запись среды выполнения, отправляет
события и завершается.

Основные файлы среды выполнения:

- `.pf/process-forge.yaml`;
- `.pf/contexts/`;
- `.pf/runs/`;
- `.pf/assignments/`;
- `.pf/artifacts/`;
- `.pf/reviews/`;
- `.pf/handoffs/`;
- `.pf/runtime/events/events.ndjson`.

Долгоживущий watcher или runner может появиться отдельным слоем позже, но ядро
среды выполнения не требует демона.

## Центральный raw ingress workplace

Нативный payload агента сначала записывается в приватный Raw Event Journal
workplace: `<workplace>/runtime/agent-events/`, а не прямо в project event.
Там находятся raw shards, dedupe/index state, quarantine и replay checkpoints.
Agent Ledger и Runtime service state/logs также относятся к workplace;
проектные records остаются в `.pf/runtime/`.

В архив входят `src/processforge_core`, `tools/processforge.py` и
`tools/pf_runtime/*`, но не raw journals, chat transcripts, quarantine,
event indexes и replay checkpoints.

## Требования к среде выполнения

Для среды выполнения рекомендуется Python 3.11+. Python 3.10+ допустим только
когда текущие тесты подтверждают совместимость. Также нужны зависимости
Python-пакетов из `requirements.txt`, включая `PyYAML`, файловая система с
UTF-8 и доступ на чтение и запись к дистрибутиву ProcessForge, workplace и
папкам проекта.

Обычное использование не требует PowerShell, Git, демона или фонового процесса.
Git нужен только для интеграции с системой контроля версий или для проверок
разработки и релиза.
# Runtime, Ledger и интерфейсы только для чтения

PF Runtime — локальный workplace-scoped host жизненного цикла, scheduler и IPC,
а не второй PF Core. Каноническая привязка `session -> project` принадлежит
Agent Ledger; карты Runtime являются только восстанавливаемым кэшем. После
удаления кэша маршрут восстанавливается из Ledger, а запрос к другому проекту
для той же session отклоняется.

Тонкий адаптер Codex передаёт наблюдаемые факты в существующий путь событий PF.
Read-only MCP предоставляет `pf.project_state`, `pf.work_state`, `pf.resolve`
и `pf.workplace_state` только для уже привязанной Ledger session.

## Декларативные технические проекции

Process definition может объявить у стадии `technical_obligations`. Runtime Host
читает эту декларацию и записывает только отдельный generated-файл в
`.pf/artifacts/projections/`; stage business logic не переносится в Runtime, а
semantic reports, handoffs и body выходных артефактов не переписываются.

Первый projector `required-output-readiness` привязан к стадии `collect`
`process-supervisor`. Он использует assignment, состояние worker из Inspector и
fingerprint required outputs. Состояние бывает `current`, `stale`, `missing` или
`invalid`; projection rebuild выполняется через `runtime-host
rebuild-projections`, а CLI-проверка без daemon — через `runtime-host
projection-doctor`.
