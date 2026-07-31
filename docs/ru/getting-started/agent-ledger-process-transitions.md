# Agent Ledger и переходы процессов

Agent Ledger - это журнал вахтёра для явки и состояния сессий, управляемый
CLI-командами. Это не отдельный агент. Для стандартного single-agent режима
`1-1-1-1` используйте session aliases и не выдавайте explicit lease самому себе:

```bash
python bin/pf.py session-start --workplace <workplace> --project-root . --agent primary-agent --process task-batch-execution
python bin/pf.py session-heartbeat --project-root .
python bin/pf.py session-status --project-root . --json
python bin/pf.py session-end --project-root .
```

Создайте workplace, зарегистрируйте agents и проверьте доступность роли:

```bash
python bin/pf.py workplace-init --workplace <workplace> --apply
python bin/pf.py agent-register --workplace <workplace> --agent director-local --role director --role orchestrator
python bin/pf.py agent-checkin --workplace <workplace> --agent director-local --role director --role orchestrator
python bin/pf.py agent-availability --workplace <workplace> --role director --json
```

Создайте route и handoff package в проекте:

```bash
python bin/pf.py process-route-list --project-root .
python bin/pf.py handoff-create --project-root . --route <route-id> --from-run <run-id> --id <handoff-id> --apply
python bin/pf.py handoff-status --project-root . --handoff <handoff-id> --workplace <workplace> --json
python bin/pf.py agent-director-tick --workplace <workplace> --project-root .
```

Для shell workers используйте `orchestrator-shell-plan-*`:

```bash
python bin/pf.py orchestrator-shell-plan-create --project-root . --run orchestrated-work --title "Orchestrated work" --answers examples/orchestrator-shell-agents/minimal/orchestrator-shell-agent-plan.yaml --apply
python bin/pf.py orchestrator-shell-plan-apply --project-root . --run orchestrated-work --workplace <workplace> --model <model> --apply
```

Поля shell-agent plan задают поведение. `allow_write_scope_overlap: true` меняет
overlap policy в generated assignment и capsule, а также supervisor scheduling
для этого plan. `subagent_policy` копируется в capsule и проверяется командой
`worker-run collect`.

`--model` необязателен. Если он указан, модель применяется ко всем shell
workers в plan и передаётся через assignment/capsule metadata,
`PF_AGENT_MODEL` и shell command model arguments.

После apply смотрите `.pf/runs/<run-id>/config-resolution-report.yaml`: там
записано разрешённое поведение для driver, model, overlap, start policy, outputs и
subagent reports.

Правило границы: Agent Ledger записывает check-in/check-out, presence и leases;
Agent Director использует эти записи для routes, handoffs, leases и
continuations; Process Execution Inspector (`execution-inspector-*` или
совместимые `supervisor-*`) проверяет состояние выполнения assigned worker и
required outputs; Worker Agent выполняет capsule task. `agent-director-tick` не
должен создавать `.pf/runtime/agent-runs/` process state, а inspector ticks не
должны писать workplace ledger или lease files.
