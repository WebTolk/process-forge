# Agent Session Model

The atomic ProcessForge execution unit is `1-1-1-1`:

- 1 human operator
- 1 primary agent session
- 1 project
- 1 active process or run

A Primary Agent Session is one agent launch in one project for one active
process/run. In simple mode that agent executes the process sequentially,
runs CLI checks, passes gates, writes artifacts/reports/handoffs, and ends the
session.

Session presence records include `agent_id`, `session_id`, `project_root`
reference, optional `project_id`, `process_id`, optional `run_id`, `roles`,
`started_at`, `last_seen_at`, optional `finished_at`, and `status`.

## Execution Modes

`single_agent`: one primary agent sequentially executes a process in one
project. This is the default `.pf` flow and is intentionally close to the old
legacy local style of one agent following a project-local process.

`single_agent_with_subagents`: one primary agent owns the process but may call
subagents for bounded analysis or checks. Subagent outputs are reports/artifacts
inside the current run; they are not workplace agents unless they explicitly
register and check in.

`orchestrated_agents`: Agent Director or Orchestrator coordinates multiple
agent sessions. Each worker is still a separate `1-1-1-1` session with its own
assignment, capsule, scope, `session_id`, and lifecycle.

`process_factory`: multiple process runs are connected through process routes,
handoffs, and continuations. Director coordinates transfers between processes;
each executor still works inside an agent session.

## Roles In Single-Agent Mode

The Operator sets the task and accepts the result.

The Primary Agent owns the process/run, performs the work, runs CLI checks,
records iterations, writes artifacts, and creates the final report/handoff.

Worker is not a separate participant. It is the same primary agent session
during the execution phase.

Inspector is not a separate participant. It is the primary agent using CLI
checks, process gates, and self-checks.

Agent Ledger exists in all modes, but it is a CLI-managed file ledger, not a
separate watchman agent. Agents check in at session start, heartbeat during long
work, and check out before leaving.

Agent Director is not required in single-agent mode. Process Supervisor /
Execution Inspector is not required unless the process launches external
runtime workers.

Simple single-agent sessions do not require explicit manual leases in the MVP.
Explicit leases are for multi-agent, handoff, and runtime-worker scenarios.

## Agent Id And Session Id

`agent_id` identifies who the agent is. `session_id` identifies one concrete
arrival: terminal window, project, process/run, or work period.

The same `agent_id` may have multiple active `session_id` values, for example
two terminal windows working on two projects. Session-safe presence is stored
under:

```text
<workplace>/runtime/agent-presence/<agent-id>/<session-id>.json
```

Project-local current session reference is stored under:

```text
.pf/runtime/current-session.json
```

These runtime files are private and are not part of the public release archive.

## Session Commands

Use either the ledger command names or the simple session aliases:

```bash
python bin/pf.py session-start --workplace <workplace> --project-root <project> --agent primary-agent --process task-batch-execution
python bin/pf.py session-heartbeat --project-root <project>
python bin/pf.py session-status --project-root <project> --json
python bin/pf.py session-end --project-root <project>
```

The aliases are thin wrappers over `agent-checkin`, `agent-heartbeat`,
`agent-status`, and `agent-checkout`.

## Conversation capture limit

For the current Codex adapter, a `UserPromptSubmit` can record the operator
prompt when project and session attribution are present. PF-owned codex-exec
worker input summaries and collectible expected reports can also be recorded
with explicit provenance checks. Generic interactive assistant responses and
host subagent messages are not currently captured automatically.
