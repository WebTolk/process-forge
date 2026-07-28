# Tool Register

## Purpose

Register a workplace tool capability provider through proposal, healthcheck definition, registry update, and review.

## When to use

Use this built-in process when its stated purpose matches the assignment.

## Execution mode

`single_agent`

## Coordination requirements

`simple_allowed`

## Roles and responsibilities

Roles are declared in `processes/core/tool-register.yaml`; responsibility boundaries separate operator, primary agent, Director, Inspector, worker, and CLI tool duties.

## Stages

- `intake`: Capture tool id, capability, command, status, and healthcheck.
- `registry-update`: Update registries/tools.yaml without storing secrets.

## Artifacts

- `tool-definition`: Tool Definition
- `tool-registration-request`: Tool Registration Request
- `validation-report`: Validation Report
- `review`: Review

## Gates and acceptance criteria

Run `python bin/pf.py process-doctor --project-root . --process tool-register --contract-only` before treating a changed process as valid.

## Error handling

`none`

## Handoff / transition behavior

See `stage_completion`, `run_completion`, and `process_transitions` in the process YAML.

## Example run

`python bin/pf.py process-describe --project-root . --process tool-register`

## CLI checks

`python bin/pf.py builtin-process-catalog-doctor --root . --public`

## What this process demonstrates

This process is a public stable built-in reference for the ProcessForge process catalog contract.
