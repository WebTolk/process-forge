# Process Supervisor

Process id: `process-supervisor`

This built-in process describes the file-first supervisor loop for bounded
worker execution. It prepares assignment capsules and worker prompts, builds a
runtime command from a neutral driver manifest, starts shell workers when
explicitly configured, observes their exit state, and collects expected outputs.

## Stages

- `prepare`: create assignment capsule, worker launch prompt, `command.json`,
  and `status.json`.
- `start`: launch the selected shell runtime driver and write process, log,
  heartbeat, and exit records.
- `collect`: verify required outputs and expected report before marking the
  task complete.

## Public Outputs

- `.pf/runtime/agent-runs/<run-id>/<task-id>/status.json`
- `.pf/runtime/agent-runs/<run-id>/<task-id>/command.json`
- `.pf/runtime/agent-runs/<run-id>/<task-id>/process.json`
- `.pf/runtime/agent-runs/<run-id>/<task-id>/stdout.log`
- `.pf/runtime/agent-runs/<run-id>/<task-id>/stderr.log`
- `.pf/runtime/agent-runs/<run-id>/<task-id>/exit.json`
- `.pf/runtime/agent-runs/<run-id>/<task-id>/collection-report.md`
