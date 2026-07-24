# Runtime Supervisor Minimal Example

This example shows a supervised two-worker run that uses the neutral
`test-echo-worker` runtime driver. The second worker depends on the first, so
both can write under `.pf/artifacts/**` without being treated as parallel
writers.

```bash
python bin/pf.py orchestrator-plan create --project-root <project-root> --run supervised-run --title "Supervised run" --answers examples/runtime-supervisor/minimal/orchestrator-task-plan.yaml --apply
python bin/pf.py orchestrator-plan apply --project-root <project-root> --run supervised-run --apply
python bin/pf.py supervisor run --project-root <project-root> --run supervised-run --max-ticks 2 --interval 0
python bin/pf.py run-status --project-root <project-root> --run supervised-run
```
