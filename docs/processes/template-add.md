# Template Add

## Purpose

Add a simple reusable template folder with README guidance and optional registry update.

## When to use

Use this built-in process when its stated purpose matches the assignment.

## Execution mode

`single_agent`

## Coordination requirements

`simple_allowed`

## Roles and responsibilities

Roles are declared in `processes/core/template-add.yaml`; responsibility boundaries separate operator, primary agent, Director, Inspector, worker, and CLI tool duties.

## Stages

- `intake`: Capture template type, id, source, and target use case.
- `template-folder-creation`: Create templates/file/<template-id>/ with README and payload files.

## Artifacts

- `template-package`: Template Package
- `template-add-request`: Template Add Request
- `validation-report`: Validation Report
- `review`: Review

## Gates and acceptance criteria

Run `python bin/pf.py process-doctor --project-root . --process template-add --contract-only` before treating a changed process as valid.

## Error handling

`none`

## Handoff / transition behavior

See `stage_completion`, `run_completion`, and `process_transitions` in the process YAML.

## Example run

`python bin/pf.py process-describe --project-root . --process template-add`

## CLI checks

`python bin/pf.py builtin-process-catalog-doctor --root . --public`

## What this process demonstrates

This process is a public stable built-in reference for the ProcessForge process catalog contract.
