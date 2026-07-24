# Runtime Auditor Report

Read-only native subagent audit. The subagent did not edit files.

## Findings

### High: Detached worker-run needed a durable observe path

The auditor confirmed that `worker-run start --detach` wrote `running` state
but the supervisor did not yet call the observe path. Without that, a detached
worker could remain reported as `running` after the CLI process exited.

Status: fixed in this stabilization pass. `supervisor tick` now observes
running workers before scheduling more work and records completion, failure, or
timeout from process handles/PIDs and expected report state.

### High: Supervisor watcher was blocking, not detach/observe based

The auditor confirmed that `command_supervisor_tick()` called
`command_worker_run_start()` without detached mode and immediately tried to
collect. That made `max_parallel_workers` ineffective for long workers.

Status: fixed. Supervisor scheduling now starts workers with detached mode,
tracks running scopes, observes running tasks on later ticks, and collects
completed reports.

### Medium: Timeout proof was incomplete for worker runtime

The auditor noted that blocking worker-run timeout used direct `proc.kill()`
and detached timeout handling was not wired through the supervisor.

Status: improved. Detached worker observation now detects timeout, terminates
the process/PID, writes `timed_out` status and `exit.json`, and supervisor
propagates failure.

### Medium: Full shell-agent supervisor matrix was missing

Status: fixed by `tools/smoke_full_shell_agents_supervisor.py`.

### Low: Env isolation had targeted proof for `test-shell-agent` only

Status: retained and expanded in the full supervisor smoke for supervised shell
workers.
