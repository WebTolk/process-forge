# Bug Fix

## Purpose

Reproduce, fix, verify, and document a defect.

## When to use

Use this built-in process when its stated purpose matches the assignment.

## Execution mode

`single_agent`

## Coordination requirements

`simple_allowed`

## Roles and responsibilities

Roles are declared in `processes/bug-fix.yaml`; responsibility boundaries separate operator, primary agent, Director, Inspector, worker, and CLI tool duties.

## Stages

- `reproduce`: Capture expected and actual behavior.
- `fix`: Apply the smallest coherent fix.
- `verify`: Check fix and regression risk.

## Artifacts

- `reproduction-report`: Reproduction Report
- `change-summary`: Change Summary
- `test-report`: Test Report
- `changed-files`: Changed Files
- `review-findings`: Review Findings

## Gates and acceptance criteria

Run `python bin/pf.py process-doctor --project-root . --process bug-fix --contract-only` before treating a changed process as valid.

## Error handling

`none`

## Handoff / transition behavior

See `stage_completion`, `run_completion`, and `process_transitions` in the process YAML.

## Example run

`python bin/pf.py process-describe --project-root . --process bug-fix`

## CLI checks

`python bin/pf.py builtin-process-catalog-doctor --root . --public`

## What this process demonstrates

This process is a public stable built-in reference for the ProcessForge process catalog contract.
