# ADR: Director, Ledger, Execution Inspector, And Worker Boundary

Date: 2026-07-26

## Status

Accepted

## Context

ProcessForge has Agent Ledger, Agent Director, Process Supervisor, runtime
drivers, worker-run, process routes, handoffs, continuations, and orchestrator
shell-agent flows. The word `supervisor` can be read as a manager/director,
but the implemented component is a runtime execution checker for assigned
worker tasks.

## Decision

Keep `process-supervisor`, `.pf/runtime/supervisor/`, `supervisor`,
`supervisor-tick`, `supervisor-run`, `supervisor-status`, and
`supervisor-stop` as stable technical compatibility names.

Use Process Execution Inspector as the semantic role name in display titles,
docs, prompts, process definitions, and CLI help.

Add thin CLI aliases:

- `execution-inspector-tick`
- `execution-inspector-run`
- `execution-inspector-status`
- `execution-inspector-stop`

The aliases call the existing supervisor handlers and introduce no parallel
runtime logic.

## Responsibility Split

Agent Ledger records agent check-in/check-out, presence, stale/offline status,
and lease/key lifecycle.

Agent Director coordinates routes, handoffs, leases, returns, finalization, and
continuations. It may read ledger state and ask the execution inspector for
runtime state.

Process Execution Inspector verifies assigned task runtime execution, including
status, process state, heartbeat, exit code, required outputs, expected reports,
and collection.

Worker Agent performs the assigned capsule task.

## Consequences

Documentation can use the clearer Execution Inspector term without breaking
existing scripts and archive consumers.

Tests must prove that Director can grant leases and mark handoffs ready without
creating worker runtime files, and that the inspector can create worker runtime
proof without writing workplace ledger or lease files.
