# Process Supervisor

The process supervisor is a bounded file-first loop for worker task execution.
It observes `.pf/runs/`, `.pf/assignments/`, and `.pf/runtime/agent-runs/`.
It can prepare worker state, start neutral shell drivers, observe detached
workers, collect required outputs, and write supervisor state.

Runtime state layout:

- `.pf/runtime/agent-runs/<run-id>/<task-id>/status.json`
- `.pf/runtime/agent-runs/<run-id>/<task-id>/command.json`
- `.pf/runtime/agent-runs/<run-id>/<task-id>/process.json`
- `.pf/runtime/agent-runs/<run-id>/<task-id>/heartbeat.json`
- `.pf/runtime/agent-runs/<run-id>/<task-id>/exit.json`
- `.pf/runtime/agent-runs/<run-id>/<task-id>/stdout.log`
- `.pf/runtime/agent-runs/<run-id>/<task-id>/stderr.log`
- `.pf/runtime/supervisor/state.json`
- `.pf/runtime/supervisor/last-tick-report.md`

Primary commands:

```bash
python .pf/runtime/bin/pf.py worker-run prepare --project-root . --task docs-worker --driver manual
python .pf/runtime/bin/pf.py worker-run start --project-root . --task test-worker --driver test-echo-worker
python .pf/runtime/bin/pf.py worker-run start --project-root . --task test-worker --driver test-echo-worker --detach
python .pf/runtime/bin/pf.py worker-run status --project-root . --task test-worker
python .pf/runtime/bin/pf.py worker-run collect --project-root . --task test-worker
python .pf/runtime/bin/pf.py supervisor tick --project-root . --run example-run
python .pf/runtime/bin/pf.py supervisor run --project-root . --run example-run --max-ticks 5
```

`worker-run start` waits by default. `--detach` starts the OS process, records
`running` state, `process.json`, stdout/stderr paths, and returns without
waiting. Later supervisor ticks observe the process by handle or PID, trust
`exit.json` as the durable terminal process result when it exists, update
`status.json`, and collect completed reports.

For shell-launched proof workers, `heartbeat.json` is mandatory and is written
at `.pf/runtime/agent-runs/<run-id>/<task-id>/heartbeat.json`. A fast worker
still leaves a heartbeat proof artifact. The minimal machine-readable fields
are `schema_version`, `run_id`, `task_id`, `status`, `pid`, `timestamp`, and
`sequence`. `heartbeat.json` is the live/current process proof; `exit.json` is
the final process result.

`supervisor tick` is one observe/start/collect pass. It respects task dependencies from `depends_on` and
`dependencies`, starts ready workers up to `max_parallel_workers`, observes
already running workers before starting more, and blocks unrelated active
writers when their write scopes overlap. Sequential tasks may share an artifact
scope when one task depends on the other.

The supervisor is not a long-running service requirement. `supervisor run`
is bounded by `--max-ticks` or by the selected profile. After the main tick
loop, it performs a bounded final observe/collect drain for already running
detached workers. That drain does not start new tasks; it only observes
existing runtime state, reads `exit.json` / `heartbeat.json`, synchronizes
`status.json`, and collects successful completed reports. A report artifact is
task output, not success proof; a lost process without `exit.json` is recorded
as `unknown_exit`/failed rather than inferred as completed.

Native subagents launched by a host AI environment are not PF runtime drivers.
They may consume ProcessForge assignment and capsule files, but their process
lifecycle is outside this supervisor contract.
