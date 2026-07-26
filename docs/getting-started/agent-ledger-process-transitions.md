# Agent Ledger and Process Transitions

Create a workplace, register agents, and check availability:

```bash
python bin/pf.py workplace-init --workplace <workplace> --apply
python bin/pf.py agent-register --workplace <workplace> --agent director-local --role director --role orchestrator
python bin/pf.py agent-checkin --workplace <workplace> --agent director-local --role director --role orchestrator
python bin/pf.py agent-availability --workplace <workplace> --role director --json
```

Create route and handoff packages in a project:

```bash
python bin/pf.py process-route-list --project-root .
python bin/pf.py handoff-create --project-root . --route <route-id> --from-run <run-id> --id <handoff-id> --apply
python bin/pf.py handoff-status --project-root . --handoff <handoff-id> --workplace <workplace> --json
python bin/pf.py agent-director-tick --workplace <workplace> --project-root .
```

For shell workers:

```bash
python bin/pf.py orchestrator-shell-plan-create --project-root . --run orchestrated-work --title "Orchestrated work" --answers examples/orchestrator-shell-agents/minimal/orchestrator-shell-agent-plan.yaml --apply
python bin/pf.py orchestrator-shell-plan-apply --project-root . --run orchestrated-work --workplace <workplace> --apply
```

Shell-agent plan fields are behavioral. `allow_write_scope_overlap: true` changes generated assignment and capsule overlap policy and supervisor scheduling for that plan. Subagent policy is copied into the capsule and enforced by `worker-run collect`.

After apply, inspect `.pf/runs/<run-id>/config-resolution-report.yaml` to see the resolved driver, overlap, start, output, and subagent-report behavior.
