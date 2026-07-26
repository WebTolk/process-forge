# Process Supervisor

Process supervisor - историческое техническое имя Process Execution Inspector.
Это ограниченный file-first цикл для проверки worker task execution, а не
director или agent manager.
Он читает `.pf/runs/`, `.pf/assignments/`, `.pf/runtime/agent-runs/`,
подготавливает worker state, запускает нейтральные shell driver-ы, собирает
required outputs и пишет supervisor state.

Execution Inspector не выдает leases, не пишет workplace agent ledger events,
не выбирает process routes, не принимает и не финализирует handoffs, не
назначает agents и не решает ownership project/run. См.
[Граница Director, Ledger, Inspector и Worker](director-ledger-inspector-boundary.md).

Он также не нужен для стандартного single-agent flow. В `single_agent` mode
primary agent использует CLI checks, gates и self-check как inspector. Этот
runtime inspector loop нужен, когда запускаются external runtime workers и
ProcessForge должен наблюдать process state, heartbeat, exit и outputs.

Runtime layout:

- `.pf/runtime/agent-runs/<run-id>/<task-id>/status.json`
- `.pf/runtime/agent-runs/<run-id>/<task-id>/command.json`
- `.pf/runtime/agent-runs/<run-id>/<task-id>/process.json`
- `.pf/runtime/agent-runs/<run-id>/<task-id>/heartbeat.json`
- `.pf/runtime/agent-runs/<run-id>/<task-id>/exit.json`
- `.pf/runtime/agent-runs/<run-id>/<task-id>/stdout.log`
- `.pf/runtime/agent-runs/<run-id>/<task-id>/stderr.log`
- `.pf/runtime/supervisor/state.json`
- `.pf/runtime/supervisor/last-tick-report.md`

Основные команды:

```bash
python .pf/runtime/bin/pf.py worker-run prepare --project-root . --task docs-worker --driver manual
python .pf/runtime/bin/pf.py worker-run start --project-root . --task test-worker --driver test-echo-worker
python .pf/runtime/bin/pf.py worker-run start --project-root . --task test-worker --driver test-echo-worker --detach
python .pf/runtime/bin/pf.py worker-run status --project-root . --task test-worker
python .pf/runtime/bin/pf.py worker-run collect --project-root . --task test-worker
python .pf/runtime/bin/pf.py supervisor tick --project-root . --run example-run
python .pf/runtime/bin/pf.py supervisor run --project-root . --run example-run --max-ticks 5
python .pf/runtime/bin/pf.py execution-inspector-tick --project-root . --run example-run
python .pf/runtime/bin/pf.py execution-inspector-run --project-root . --run example-run --max-ticks 5
```

`supervisor tick` учитывает `depends_on` и `dependencies`. Последовательные
задачи могут иметь общий artifact scope, если одна задача зависит от другой;
несвязанные активные writer-ы по-прежнему блокируются non-overlap guard.

Для shell-launched proof worker файл `heartbeat.json` обязателен и лежит в
`.pf/runtime/agent-runs/<run-id>/<task-id>/heartbeat.json`. Даже быстрый worker
оставляет heartbeat proof artifact. Минимальные machine-readable поля:
`schema_version`, `run_id`, `task_id`, `status`, `pid`, `timestamp`,
`sequence`. `heartbeat.json` описывает текущий/live process proof, а
`exit.json` хранит финальный результат процесса.

Supervisor не является обязательным демоном. `supervisor run` ограничен
`--max-ticks` или профилем и завершается после этих tick-ов.

Native subagents, которые запускает внешняя AI-среда, не являются PF runtime
drivers. Они могут использовать assignment и capsule файлы ProcessForge, но их
process lifecycle находится вне этого supervisor contract.
