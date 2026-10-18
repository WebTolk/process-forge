# Multi-Agent Orchestration Quickstart

Use this optional flow inside an onboarded project when the chosen process
permits delegation. Ordinary Garage work does not require it. Review the plan
before apply: each worker needs explicit inputs, read/write scope, outputs and
dependencies. Keep one writer per scope and preserve immutable capsules.

```bash
python .pf/runtime/bin/pf.py orchestrator-plan create --project-root . --run example-run --title "Example multi-agent run" --apply
python .pf/runtime/bin/pf.py orchestrator-plan validate --project-root . --plan .pf/runs/example-run/orchestrator-plan.yaml
python .pf/runtime/bin/pf.py orchestrator-plan apply --project-root . --plan .pf/runs/example-run/orchestrator-plan.yaml --apply
python .pf/runtime/bin/pf.py orchestrator-plan status --project-root . --run example-run
python .pf/runtime/bin/pf.py worker-launch-prompt create --project-root . --task fixture-worker-a --apply
```

Flat aliases are also available:

- `orchestrator-plan-create`
- `orchestrator-plan-validate`
- `orchestrator-plan-apply`
- `orchestrator-plan-status`
- `worker-launch-prompt-create`
- `runtime-driver-list`
- `worker-run-prepare`
- `worker-run-start`
- `worker-run-collect`
- `supervisor-run`

The generated example uses `fixture-worker-a` and `fixture-worker-b`. Replace
the sample work and use the task id actually present in your plan. The source
template is `templates/orchestrator-task-plan.yaml` in the distribution; a
linked project does not receive that entire directory.

Plans may include:

```yaml
runtime:
  default_driver: manual
  supervisor_profile: default
  start_policy: manual
```

Workers may set `runtime_driver` and `depends_on`. The default `manual` driver
does not start a process; use [Runtime driver and supervisor quickstart](runtime-driver-supervisor.md)
for the bounded supervised smoke flow.

To reuse the distribution example plan, run from the ProcessForge distribution
root and point `--project-root` at an onboarded project:

```bash
python bin/pf.py orchestrator-plan create --project-root <project-root> --run example-run --title "Example multi-agent run" --answers examples/multi-agent-orchestration/minimal/orchestrator-task-plan.yaml --apply
```
