# Full Shell Agents Supervisor Test Report

Command:

```bash
python -u tools/smoke_full_shell_agents_supervisor.py
```

Result: PASS.

Coverage:

- fast shell-agent success with runtime artifacts
- detached slow worker observed across supervisor ticks
- heartbeat file advances while the worker is running
- dependency waits until upstream task is collected
- two non-overlapping workers can start in parallel
- overlapping active writer scopes are not started together
- nonzero shell-agent exit propagates supervisor failure
- timeout writes `timed_out` state and `exit.json`
- parent `PF_LEAK_TEST_*` environment variables do not reach isolated workers

Required artifacts verified by the smoke:

- `status.json`
- `command.json`
- `process.json`
- `stdout.log`
- `stderr.log`
- `heartbeat.json`
- `exit.json`
- expected markdown report under `.pf/artifacts/`
