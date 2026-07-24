# Process Supervisor

Process supervisor - это ограниченный file-first цикл для worker task execution.
Он читает `.pf/runs/`, `.pf/assignments/`, `.pf/runtime/agent-runs/`,
подготавливает worker state, запускает нейтральные shell driver-ы, собирает
required outputs и пишет supervisor state.

Runtime layout:

- `.pf/runtime/agent-runs/<run-id>/<task-id>/status.json`
- `.pf/runtime/agent-runs/<run-id>/<task-id>/command.json`
- `.pf/runtime/agent-runs/<run-id>/<task-id>/process.json`
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
```

`supervisor tick` учитывает `depends_on` и `dependencies`. Последовательные
задачи могут иметь общий artifact scope, если одна задача зависит от другой;
несвязанные активные writer-ы по-прежнему блокируются non-overlap guard.

Supervisor не является обязательным демоном. `supervisor run` ограничен
`--max-ticks` или профилем и завершается после этих tick-ов.
