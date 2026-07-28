# Platform Contract Install

## Purpose

Create or update a platform contract mapping capabilities, knowledge packages, tools, MCP, and templates.

## When to use

Use this built-in process when its stated purpose matches the assignment.

## Execution mode

`single_agent`

## Coordination requirements

`simple_allowed`

## Roles and responsibilities

Roles are declared in `processes/core/platform-contract-install.yaml`; responsibility boundaries separate operator, primary agent, Director, Inspector, worker, and CLI tool duties.

## Stages

- `platform-definition`: Capture platform id, project types, capabilities, and resource mapping.
- `contract-creation`: Write platform contract and registry entry, then run platform doctor.

## Artifacts

- `platform-contract`: Platform Contract
- `platform-contract-proposal`: Platform Contract Proposal
- `validation-report`: Validation Report
- `review`: Review

## Gates and acceptance criteria

Run `python bin/pf.py process-doctor --project-root . --process platform-contract-install --contract-only` before treating a changed process as valid.

## Error handling

`none`

## Handoff / transition behavior

See `stage_completion`, `run_completion`, and `process_transitions` in the process YAML.

## Example run

`python bin/pf.py process-describe --project-root . --process platform-contract-install`

## CLI checks

`python bin/pf.py builtin-process-catalog-doctor --root . --public`

## What this process demonstrates

This process is a public stable built-in reference for the ProcessForge process catalog contract.
