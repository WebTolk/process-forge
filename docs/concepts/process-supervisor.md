# Process Supervisor

The process supervisor is a bounded file-first loop for worker task execution.
It observes `.pf/runs/`, `.pf/assignments/`, and `.pf/runtime/agent-runs/`.
It can prepare worker state, start neutral shell drivers, collect required
outputs, and write supervisor state.

Runtime state layout:

- `.pf/runtime/agent-runs/<run-id>/<task-id>/status.json`
- `.pf/runtime/agent-runs/<run-id>/<task-id>/command.json`
- `.pf/runtime/agent-runs/<run-id>/<task-id>/process.json`
- `.pf/runtime/agent-runs/<run-id>/<task-id>/exit.json`
- `.pf/runtime/agent-runs/<run-id>/<task-id>/stdout.log`
- `.pf/runtime/agent-runs/<run-id>/<task-id>/stderr.log`
- `.pf/runtime/supervisor/state.json`
- `.pf/runtime/supervisor/last-tick-report.md`

Primary commands:

```bash
python .pf/runtime/bin/pf.py worker-run prepare --project-root . --task docs-worker --driver manual
python .pf/runtime/bin/pf.py worker-run start --project-root . --task test-worker --driver test-echo-worker
python .pf/runtime/bin/pf.py worker-run status --project-root . --task test-worker
python .pf/runtime/bin/pf.py worker-run collect --project-root . --task test-worker
python .pf/runtime/bin/pf.py supervisor tick --project-root . --run example-run
python .pf/runtime/bin/pf.py supervisor run --project-root . --run example-run --max-ticks 2
```

`supervisor tick` respects task dependencies from `depends_on` and
`dependencies`. Sequential tasks may share an artifact scope when one task
depends on the other; unrelated active writers are still blocked by the
non-overlap guard.

The supervisor is not a long-running service requirement. `supervisor run`
is bounded by `--max-ticks` or by the selected profile and exits after those
ticks.
