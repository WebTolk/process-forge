# Runtime And MCP Autostart Implementation

## Implemented

- `runtime autostart status|install|remove` manages one deterministic current-user Windows Task Scheduler task per workplace.
- Task Scheduler owns foreground `runtime serve`, uses an interactive least-privilege principal, logon delay, unlimited runtime, singleton protection and bounded restart-on-failure.
- Install/remove are dry-run by default and require `--apply`; drift replacement/removal requires an explicit override.
- `codex-mcp status|install|remove` manages the host-owned stdio MCP registration through Codex CLI.
- Codex MCP install is opt-in and idempotent; drift replacement and forced removal are explicit.
- Distribution-root and Python overrides support setup from a source checkout against a stable installed distribution.

## Verification

- Python compile: PASS.
- Focused lifecycle smoke, including Task Scheduler console XML re-encoding: PASS.
- CLI help for both command groups: PASS.
- Real Windows Task Scheduler install: PASS, task `ProcessForge Runtime 5365635d5b5e`.
- Real ownership transfer: old detached Runtime stopped; scheduled task launched Runtime PID `3828`; Runtime reached `status=ready`.
- Exact scheduled-task status and removal dry-run: PASS.
- Existing Codex MCP registration resolved as exact installed match and install dry-run was idempotent.

## Known Condition

The scheduled task currently executes the restored installed PF 1.1.0. Its known status/scheduler timeout remains visible as `health=degraded`; the task itself is running and `/readyz` is ready. Candidate 1.2.1 contains the separately qualified Runtime timeout fix.
