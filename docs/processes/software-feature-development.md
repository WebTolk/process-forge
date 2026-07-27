# Software Feature Development

## Purpose

Govern a software feature from intake through release and evolution.

## When to use

Use this built-in process when its stated purpose matches the assignment.

## Execution mode

`single_agent`

## Coordination requirements

`simple_allowed`

## Roles and responsibilities

Roles are declared in `processes/software-feature-development.yaml`; responsibility boundaries separate operator, primary agent, Director, Inspector, worker, and CLI tool duties.

## Stages

- `intake`: Capture goal and scope.
- `architecture`: Define design and implementation plan.
- `implementation`: Make bounded changes.
- `assurance`: Verify behavior and risks.

## Artifacts

- `brief`: Brief
- `scope`: Scope
- `implementation-plan`: Implementation Plan
- `change-summary`: Change Summary
- `test-report`: Test Report
- `decision-log`: Decision Log
- `changed-files`: Changed Files
- `review-findings`: Review Findings

## Gates and acceptance criteria

Run `python bin/pf.py process-doctor --project-root . --process software-feature-development --contract-only` before treating a changed process as valid.

## Error handling

`none`

## Handoff / transition behavior

See `stage_completion`, `run_completion`, and `process_transitions` in the process YAML.

## Example run

`python bin/pf.py process-describe --project-root . --process software-feature-development`

## CLI checks

`python bin/pf.py builtin-process-catalog-doctor --root . --public`

## What this process demonstrates

This process is a public stable built-in reference for the ProcessForge process catalog contract.
