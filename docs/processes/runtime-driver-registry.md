# Runtime Driver Registry

## Purpose

Govern neutral runtime driver manifests, registry entries, and validation before worker process execution.

## When to use

Use this built-in process when its stated purpose matches the assignment.

## Execution mode

`single_agent`

## Coordination requirements

`simple_allowed`

## Roles and responsibilities

Roles are declared in `processes/core/runtime-driver-registry.yaml`; responsibility boundaries separate operator, primary agent, Director, Inspector, worker, and CLI tool duties.

## Stages

- `inventory`: List built-in, workplace, and project-local runtime driver registrations.
- `validate`: Validate driver schema, placeholder allow-list, shell-disabled defaults, and no-network policy.

## Artifacts

- `runtime-driver-registry`: Runtime Driver Registry
- `runtime-driver-validation-report`: Runtime Driver Validation Report

## Gates and acceptance criteria

Run `python bin/pf.py process-doctor --project-root . --process runtime-driver-registry --contract-only` before treating a changed process as valid.

## Error handling

`none`

## Handoff / transition behavior

See `stage_completion`, `run_completion`, and `process_transitions` in the process YAML.

## Example run

`python bin/pf.py process-describe --project-root . --process runtime-driver-registry`

## CLI checks

`python bin/pf.py builtin-process-catalog-doctor --root . --public`

## What this process demonstrates

This process is a public stable built-in reference for the ProcessForge process catalog contract.
