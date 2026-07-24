# Multi-Agent Orchestration Minimal Example

This neutral example shows how an orchestrator creates bounded worker tasks.

Run from the ProcessForge distribution root and point `--project-root` at an
onboarded project:

```bash
python bin/pf.py orchestrator-plan create --project-root <project-root> --run example-run --title "Example multi-agent run" --answers examples/multi-agent-orchestration/minimal/orchestrator-task-plan.yaml --apply
python bin/pf.py orchestrator-plan validate --project-root <project-root> --plan .pf/runs/example-run/orchestrator-plan.yaml
python bin/pf.py orchestrator-plan apply --project-root <project-root> --plan .pf/runs/example-run/orchestrator-plan.yaml --apply
python bin/pf.py worker-launch-prompt create --project-root <project-root> --task example-docs-worker --apply
```

Workers receive only their assignment, capsule, allowed scopes, required outputs, and expected report path.
