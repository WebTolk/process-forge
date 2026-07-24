# Multi-Agent Orchestration Quickstart

Use this flow inside an onboarded project.

```bash
python .pf/runtime/bin/pf.py orchestrator-plan create --project-root . --run example-run --title "Example multi-agent run" --apply
python .pf/runtime/bin/pf.py orchestrator-plan validate --project-root . --plan .pf/runs/example-run/orchestrator-plan.yaml
python .pf/runtime/bin/pf.py orchestrator-plan apply --project-root . --plan .pf/runs/example-run/orchestrator-plan.yaml --apply
python .pf/runtime/bin/pf.py orchestrator-plan status --project-root . --run example-run
python .pf/runtime/bin/pf.py worker-launch-prompt create --project-root . --task docs-worker --apply
```

Flat aliases are also available:

- `orchestrator-plan-create`
- `orchestrator-plan-validate`
- `orchestrator-plan-apply`
- `orchestrator-plan-status`
- `worker-launch-prompt-create`

The plan template is `templates/orchestrator-task-plan.yaml`.
