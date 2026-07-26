# ADR: Agent Session As The Atomic Execution Unit

Date: 2026-07-26

## Status

Accepted

## Problem

ProcessForge roles were being explained in a way that could imply every mode
requires Director, Supervisor/Execution Inspector, Worker, and Ledger as
separate participants. That is wrong for the default `.pf` flow.

## Decision

The atomic ProcessForge execution unit is an agent session:

- one human operator
- one primary agent session
- one project
- one active process or run

Single-agent mode uses one primary agent. The same agent performs work, runs
CLI checks, passes gates, writes artifacts, and closes the session.

Multi-agent mode composes multiple agent sessions and adds Agent Director or
Orchestrator coordination.

Process factory mode composes multiple process runs through routes, handoffs,
leases, and continuations. Each executor still works inside an agent session.

Agent Ledger is CLI-managed attendance/session state, not an agent.

Supervisor / Execution Inspector is only needed for external runtime workers.

Agent Director is only needed for multi-agent or process-transition
coordination.

## Consequences

The simple project-local `.pf` flow remains the default mental model.
Advanced roles appear only when the selected execution mode requires them.

Presence is session-safe: one `agent_id` can have multiple active `session_id`
records across projects or terminal windows.

Simple single-agent sessions do not require explicit manual leases in the MVP.
