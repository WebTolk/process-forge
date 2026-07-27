# Workplace Initialization

## Purpose

Initialize or update the machine-local ProcessForge workplace layer.

## When to use

Use this built-in process when its stated purpose matches the assignment.

## Execution mode

`single_agent`

## Coordination requirements

`simple_allowed`

## Roles and responsibilities

Roles are declared in `processes/workplace-initialization.yaml`; responsibility boundaries separate operator, primary agent, Director, Inspector, worker, and CLI tool duties.

## Stages

- `intake`: Capture root path, answers, Director capability, default project mode, and Director Office initialization choice.
- `terms-setup`: Create or update terms aliases.
- `registry-setup`: Create platform, knowledge, package, template, tool, and MCP registries.
- `tool-discovery`: Record configured tool providers from answers.
- `mcp-discovery`: Record configured MCP providers from answers.
- `proposal`: Present the planned workplace changes.
- `review`: Review the proposed changes.
- `apply`: Write workplace files.
- `doctor`: Validate workplace setup.

## Artifacts

- `workplace-init-answers`: Workplace Init Answers
- `workplace-init-proposal`: Workplace Init Proposal
- `workplace-doctor-report`: Workplace Doctor Report
- `workplace-bootstrap-report`: Workplace Bootstrap Report
- `workplace-ready-handoff`: Workplace Ready Handoff
- `terms-file`: Terms File
- `workplace-registries`: Workplace Registries
- `tool-registry`: Tool Registry
- `mcp-registry`: Mcp Registry
- `workplace-init-review`: Workplace Init Review
- `workplace-files`: Workplace Files

## Gates and acceptance criteria

Run `python bin/pf.py process-doctor --project-root . --process workplace-initialization --contract-only` before treating a changed process as valid.

## Error handling

`none`

## Handoff / transition behavior

See `stage_completion`, `run_completion`, and `process_transitions` in the process YAML.

## Example run

`python bin/pf.py process-describe --project-root . --process workplace-initialization`

## CLI checks

`python bin/pf.py builtin-process-catalog-doctor --root . --public`

## What this process demonstrates

This process is a public stable built-in reference for the ProcessForge process catalog contract.
