# Multi-Agent Task Orchestration

## Purpose

Orchestrator-led composition of multiple agent sessions where workers receive bounded assignments, capsules, allowed scopes, required outputs, and minimal launch prompts.

## When to use

Use this built-in process when its stated purpose matches the assignment.

## Execution mode

`orchestrated_agents`

## Coordination requirements

`organized_optional`

## Roles and responsibilities

Roles are declared in `processes/multi-agent-task-orchestration.yaml`; responsibility boundaries separate operator, primary agent, Director, Inspector, worker, and CLI tool duties.

## Stages

- `plan`: Record run metadata, worker tasks, execution modes, dependencies, scope, outputs, and integration expectations.
- `assign`: Create run, assignment-backed tasks, assignment capsules, task index, orchestration summary, and initial handoff.
- `worker-execution`: Each worker acts from its task and capsule without rebuilding full project context by default.
- `integration-review`: Orchestrator reviews worker outputs, resolves residual risks, and writes final integration report.

## Artifacts

- `orchestrator-task-plan`: Orchestrator Task Plan
- `worker-launch-prompts`: Worker Launch Prompts
- `task-index`: Task Index
- `orchestration-summary`: Orchestration Summary
- `orchestrator-handoff`: Orchestrator Handoff
- `worker-reports`: Worker Reports
- `integration-report`: Integration Report

## Gates and acceptance criteria

Run `python bin/pf.py process-doctor --project-root . --process multi-agent-task-orchestration --contract-only` before treating a changed process as valid.

## Error handling

`needs_operator`

## Handoff / transition behavior

See `stage_completion`, `run_completion`, and `process_transitions` in the process YAML.

## Example run

`python bin/pf.py process-describe --project-root . --process multi-agent-task-orchestration`

## CLI checks

`python bin/pf.py builtin-process-catalog-doctor --root . --public`

## What this process demonstrates

This process is a public stable built-in reference for the ProcessForge process catalog contract.
