# Task Batch Execution

## Purpose

Default single-agent process for one primary agent session to execute tasks sequentially inside one project/run with repeated work, debug, fix, review, and handoff iterations.

## When to use

Use this built-in process when its stated purpose matches the assignment.

## Execution mode

`single_agent`

## Coordination requirements

`simple_allowed`

## Roles and responsibilities

Roles are declared in `processes/core/task-batch-execution.yaml`; responsibility boundaries separate operator, primary agent, Director, Inspector, worker, and CLI tool duties.

## Stages

- `run-intake`: Create the run or inspect an existing active run.
- `task-planning`: Create assignment-backed tasks and attach them to the run.
- `task-execution-loop`: Record work, debug, fix, review, test, research, handoff, or note iterations for each task.
- `task-result-fixation`: Complete each task with a result summary or result artifact.
- `run-review`: Run run-doctor and task-doctor checks before final completion.
- `run-summary`: Aggregate task results into a run summary and handoff.

## Artifacts

- `run-record`: Run Record
- `task-index`: Task Index
- `task-iteration-log`: Task Iteration Log
- `task-result`: Task Result
- `run-review`: Run Review
- `run-summary`: Run Summary
- `run-handoff`: Run Handoff

## Gates and acceptance criteria

Run `python bin/pf.py process-doctor --project-root . --process task-batch-execution --contract-only` before treating a changed process as valid.

## Error handling

`none`

## Handoff / transition behavior

See `stage_completion`, `run_completion`, and `process_transitions` in the process YAML.

## Example run

`python bin/pf.py process-describe --project-root . --process task-batch-execution`

## CLI checks

`python bin/pf.py builtin-process-catalog-doctor --root . --public`

## What this process demonstrates

This process is a public stable built-in reference for the ProcessForge process catalog contract.
