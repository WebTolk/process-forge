# Process Supervisor Process Example

This example documents the built-in `process-supervisor` process. Use it after
creating a run and tasks or applying an orchestrator plan with runtime driver
settings.

```bash
python bin/pf.py runtime-driver list --project-root <project-root>
python bin/pf.py runtime-driver validate --project-root <project-root> --driver test-shell-agent
python bin/pf.py supervisor tick --project-root <project-root> --run <run-id>
python bin/pf.py supervisor run --project-root <project-root> --run <run-id> --max-ticks 5 --interval 0
```

The supervisor writes runtime proofs under `.pf/runtime/agent-runs/` and returns
non-zero status when a worker cannot be started, times out, or exits
unsuccessfully.
