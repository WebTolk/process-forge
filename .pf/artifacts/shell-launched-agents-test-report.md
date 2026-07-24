# Shell-Launched Agents Test Report

- run: `runtime-supervisor-audit-fix-shell-agents`
- timestamp: `2026-07-24T16:33:08+04:00`
- status: `passed`
- proof type: ProcessForge runtime driver and supervisor shell processes
- built-in subagents used: `no`

## Smoke Coverage

- `tools/smoke_worker_run_manual.py`: manual driver prepares state without process start.
- `tools/smoke_worker_run_shell.py`: `test-shell-agent` starts as a shell process, writes report, heartbeat, process proof, and confirms no `PF_LEAK_TEST_*` parent variable leakage.
- `tools/smoke_process_supervisor_tick.py`: supervisor tick returns non-zero when `generic-shell` has no executable.
- `tools/smoke_process_supervisor_lifecycle.py`: supervisor run starts and collects a shell-launched worker.
- `tools/smoke_shell_launched_agents_supervisor_fix.py`: combined proof for process pid, stdout lifecycle events, heartbeat pid, env isolation, and supervisor non-zero failure propagation.

## Runtime Proofs Checked In Smokes

- `.pf/runtime/agent-runs/<run>/<task>/process.json`
- `.pf/runtime/agent-runs/<run>/<task>/command.json`
- `.pf/runtime/agent-runs/<run>/<task>/stdout.log`
- `.pf/runtime/agent-runs/<run>/<task>/heartbeat.json`
- `.pf/artifacts/<task>-report.md`
