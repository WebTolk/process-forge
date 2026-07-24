# Runtime Driver And Supervisor Quickstart

Use this after `workplace-init` and `project-onboard`.

List and validate the built-in neutral drivers:

```bash
python .pf/runtime/bin/pf.py runtime-driver list --project-root .
python .pf/runtime/bin/pf.py runtime-driver validate --project-root . --driver manual
python .pf/runtime/bin/pf.py runtime-driver validate --project-root . --driver test-echo-worker
python .pf/runtime/bin/pf.py runtime-driver validate --project-root . --driver test-shell-agent
```

Prepare a manual worker run:

```bash
python .pf/runtime/bin/pf.py worker-run prepare --project-root . --task docs-worker --driver manual
python .pf/runtime/bin/pf.py worker-run status --project-root . --task docs-worker
```

Run a supervised test plan with the distribution example:

```bash
python .pf/runtime/bin/pf.py orchestrator-plan create --project-root . --run supervised-run --title "Supervised run" --answers examples/runtime-supervisor/minimal/orchestrator-task-plan.yaml --apply
python .pf/runtime/bin/pf.py orchestrator-plan apply --project-root . --run supervised-run --apply
python .pf/runtime/bin/pf.py supervisor run --project-root . --run supervised-run --max-ticks 5 --interval 0
python .pf/runtime/bin/pf.py run-status --project-root . --run supervised-run
```

The `test-echo-worker` and `test-shell-agent` drivers are for smoke tests and
demos. Real worker execution remains explicit and opt-in through driver
manifests. Supervisor ticks start shell workers detached, observe their
process state on later ticks, and collect required reports only after the
worker exits successfully.
