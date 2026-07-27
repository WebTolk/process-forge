# Testing

## Purpose

Plan, execute, and report a testing pass.

## When to use

Use this built-in process when its stated purpose matches the assignment.

## Execution mode

`single_agent`

## Coordination requirements

`simple_allowed`

## Roles and responsibilities

Roles are declared in `processes/testing.yaml`; responsibility boundaries separate operator, primary agent, Director, Inspector, worker, and CLI tool duties.

## Stages

- `plan`: Define test coverage and data.
- `execute`: Run test cases and record evidence.
- `report`: Summarize findings and residual risk.

## Artifacts

- `test-plan`: Test Plan
- `evidence-log`: Evidence Log
- `test-report`: Test Report
- `test-cases`: Test Cases

## Gates and acceptance criteria

Run `python bin/pf.py process-doctor --project-root . --process testing --contract-only` before treating a changed process as valid.

## Error handling

`none`

## Handoff / transition behavior

See `stage_completion`, `run_completion`, and `process_transitions` in the process YAML.

## Example run

`python bin/pf.py process-describe --project-root . --process testing`

## CLI checks

`python bin/pf.py builtin-process-catalog-doctor --root . --public`

## What this process demonstrates

This process is a public stable built-in reference for the ProcessForge process catalog contract.
