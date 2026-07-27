# Process Template Install

## Purpose

Add a reusable process definition template with artifact, gate, resource, and validation mapping.

## When to use

Use this built-in process when its stated purpose matches the assignment.

## Execution mode

`single_agent`

## Coordination requirements

`simple_allowed`

## Roles and responsibilities

Roles are declared in `processes/process-template-install.yaml`; responsibility boundaries separate operator, primary agent, Director, Inspector, worker, and CLI tool duties.

## Stages

- `intake`: Capture process purpose, scope, stages, artifacts, gates, and resources.
- `process-definition-creation`: Create process definition and validate it against schema.

## Artifacts

- `process-definition`: Process Definition
- `process-template-request`: Process Template Request
- `validation-report`: Validation Report
- `review`: Review

## Gates and acceptance criteria

Run `python bin/pf.py process-doctor --project-root . --process process-template-install --contract-only` before treating a changed process as valid.

## Error handling

`none`

## Handoff / transition behavior

See `stage_completion`, `run_completion`, and `process_transitions` in the process YAML.

## Example run

`python bin/pf.py process-describe --project-root . --process process-template-install`

## CLI checks

`python bin/pf.py builtin-process-catalog-doctor --root . --public`

## What this process demonstrates

This process is a public stable built-in reference for the ProcessForge process catalog contract.
