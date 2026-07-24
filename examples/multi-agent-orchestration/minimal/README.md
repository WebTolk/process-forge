# Multi-Agent Orchestration Minimal Example

This neutral example shows how an orchestrator creates bounded worker tasks.

Run inside an onboarded ProcessForge project:

```bash
python .pf/runtime/bin/pf.py orchestrator-plan create --project-root . --run example-run --title "Example multi-agent run" --answers examples/multi-agent-orchestration/minimal/orchestrator-task-plan.yaml --apply
python .pf/runtime/bin/pf.py orchestrator-plan validate --project-root . --plan .pf/runs/example-run/orchestrator-plan.yaml
python .pf/runtime/bin/pf.py orchestrator-plan apply --project-root . --plan .pf/runs/example-run/orchestrator-plan.yaml --apply
python .pf/runtime/bin/pf.py worker-launch-prompt create --project-root . --task example-docs-worker --apply
```

Workers receive only their assignment, capsule, allowed scopes, required outputs, and expected report path.
