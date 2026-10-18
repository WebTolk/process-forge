# File-First Processes

A file-first process is a repeatable workflow represented by durable files.

The minimum unit is an assignment. An assignment names the goal, role, input artifacts, allowed files, forbidden files, required outputs, quality gates, logs, and handoffs.

The process itself is defined separately so that multiple assignments can follow the same stages without copying instructions.

## Core Objects

- Process definitions describe repeatable work.
- Assignments describe one bounded execution.
- Artifacts preserve outputs.
- Reviews preserve quality decisions.
- Handoffs preserve transfer state.
- Logs preserve the work trail.
- Execution Context Packages preserve the exact context used for a task.

## Why Files

Files make the system portable, reviewable, versionable, and usable without a
service dependency. The CLI and optional Runtime adapters use the same durable
Work records; the selected process and immutable capsule remain authoritative.
Use [Garage Core](garage-core.md) for the ordinary context, state, evidence and
transition cycle.

## Status Model

Use machine-readable ids only. Human explanations belong in prose fields, not status fields.
