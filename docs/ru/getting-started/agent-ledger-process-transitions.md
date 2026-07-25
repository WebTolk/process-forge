# Agent Ledger и Process Transitions

Создайте workplace, зарегистрируйте агентов и проверьте доступность роли:

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

Для shell workers используйте `orchestrator-shell-plan-*`. Subagents разрешаются только через `subagent_policy` в capsule.
