# Runtime Driver And Execution Inspector Quickstart

Use this after `workplace-init` and `project-onboard`.

`supervisor` is the historical technical command name. In ProcessForge
semantics this loop is the Process Execution Inspector: it checks assigned task
runtime state and does not manage agent attendance, grant leases, route
processes, or finalize handoffs.

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
python .pf/runtime/bin/pf.py execution-inspector-run --project-root . --run supervised-run --max-ticks 5 --interval 0
python .pf/runtime/bin/pf.py run-status --project-root . --run supervised-run
```

The `test-echo-worker` and `test-shell-agent` drivers are for smoke tests and
demos. Real worker execution remains explicit and opt-in through driver
manifests. Execution-inspector ticks start shell workers detached, observe their
process state on later ticks, and collect required reports only after the
worker exits successfully.

`supervisor run` is a bounded loop of ticks plus a final observe/collect drain.
The drain is also bounded and does not start new tasks; it only synchronizes
already running detached workers before the command returns. `exit.json` is the
durable terminal result, `heartbeat.json` is live progress proof, `status.json`
is the supervisor-observed state, and the report artifact is output rather than
proof of `exit_code=0`.

Shell-launched proof workers create `status.json`, `command.json`,
`process.json`, `stdout.log`, `stderr.log`, `heartbeat.json`, `exit.json`, and
the configured report artifact. `heartbeat.json` lives at
`.pf/runtime/agent-runs/<run-id>/<task-id>/heartbeat.json` and contains at
least `schema_version`, `run_id`, `task_id`, `status`, `pid`, `timestamp`, and
`sequence`. It is separate from `exit.json`: heartbeat is the current process
proof, while exit records the final result.
