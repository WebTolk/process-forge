# Agent Ledger и переходы процессов

Agent Ledger хранит сведения о присутствии агентов и состоянии сессий;
им управляют CLI-команды. Это не отдельный агент. Обычная работа Garage
без сессии обходится без Ledger. Примеры ниже нужны оператору, когда явно
выбран учёт сессий или координация через Director. Для сессии одного агента
`1-1-1-1` не нужно выдавать аренду самому себе.

Команды выполняются из подключённого проекта с уже существующим workplace:

```bash
python .pf/runtime/bin/pf.py session-start --workplace <workplace> --project-root . --agent primary-agent --process task-batch-execution
python .pf/runtime/bin/pf.py session-heartbeat --project-root .
python .pf/runtime/bin/pf.py session-status --project-root . --json
python .pf/runtime/bin/pf.py session-end --project-root .
```

В подготовленном workplace зарегистрируйте агентов и проверьте доступность роли:

```bash
python .pf/runtime/bin/pf.py agent-register --workplace <workplace> --agent director-local --role director --role orchestrator
python .pf/runtime/bin/pf.py agent-checkin --workplace <workplace> --agent director-local --role director --role orchestrator
python .pf/runtime/bin/pf.py agent-availability --workplace <workplace> --role director --json
```

Посмотрите маршруты и создайте пакет передачи работы в проекте:

```bash
python .pf/runtime/bin/pf.py process-route-list --project-root .
python .pf/runtime/bin/pf.py handoff-create --project-root . --route <route-id> --from-run <run-id> --id <handoff-id> --apply
python .pf/runtime/bin/pf.py handoff-status --project-root . --handoff <handoff-id> --workplace <workplace> --json
python .pf/runtime/bin/pf.py agent-director-tick --workplace <workplace> --project-root .
```

Для исполнителей в отдельных процессах используйте `orchestrator-shell-plan-*`.
Подготовьте файл ответов по примеру дистрибутива
`examples/orchestrator-shell-agents/minimal/orchestrator-shell-agent-plan.yaml`
и передайте его фактический путь. В проект этот пример автоматически не копируется:

```bash
python .pf/runtime/bin/pf.py orchestrator-shell-plan-create --project-root . --run orchestrated-work --title "Orchestrated work" --answers <answers-file> --apply
python .pf/runtime/bin/pf.py orchestrator-shell-plan-apply --project-root . --run orchestrated-work --workplace <workplace> --model <model> --apply
```

Поля плана влияют на выполнение. `allow_write_scope_overlap: true` меняет
политику пересечения областей записи в создаваемых назначениях и капсулах,
а также планирование инспектора. Не включайте его для обычных независимых
авторов. `subagent_policy` копируется в капсулу и проверяется `worker-run collect`.

`--model` необязателен. Если он указан, модель применяется ко всем shell
workers в plan и передаётся через assignment/capsule metadata,
`PF_AGENT_MODEL` и shell command model arguments.

Уровень мышления не задаётся флагом `orchestrator-shell-plan-apply`. Его
задают в плане через `runtime.reasoning_effort` или у конкретного worker через
`reasoning_effort`; команды `worker-run prepare/start` также могут
переопределить его через `--reasoning-effort`.

После apply смотрите `.pf/runs/<run-id>/config-resolution-report.yaml`: там
записано разрешённое поведение для driver, model, reasoning effort, overlap,
start policy, outputs и subagent reports.

Правило границы: Agent Ledger записывает check-in/check-out, presence и leases;
Agent Director использует эти записи для routes, handoffs, leases и
continuations; Process Execution Inspector (`execution-inspector-*` или
совместимые `supervisor-*`) проверяет состояние выполнения assigned worker и
required outputs; Worker Agent выполняет capsule task. `agent-director-tick` не
должен создавать `.pf/runtime/agent-runs/` process state, а inspector ticks не
должны писать workplace ledger или lease files.
