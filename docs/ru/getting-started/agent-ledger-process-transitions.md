# Agent Ledger и Process Transitions

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
python bin/pf.py orchestrator-shell-plan-apply --project-root . --run orchestrated-work --workplace <workplace> --apply
```

Поля shell-agent plan задают поведение. `allow_write_scope_overlap: true` меняет overlap policy в generated assignment и capsule, а также supervisor scheduling для этого plan. `subagent_policy` копируется в capsule и проверяется командой `worker-run collect`.

После apply смотрите `.pf/runs/<run-id>/config-resolution-report.yaml`: там записано resolved поведение для driver, overlap, start policy, outputs и subagent reports.
