# Reusable Template Authoring

## Purpose

Create, register, validate, and hand off a reusable ProcessForge workplace template.

## When to use

Use this built-in process when its stated purpose matches the assignment.

## Execution mode

`single_agent`

## Coordination requirements

`simple_allowed`

## Roles and responsibilities

Roles are declared in `processes/reusable-template-authoring.yaml`; responsibility boundaries separate operator, primary agent, Director, Inspector, worker, and CLI tool duties.

## Stages

- `intake`: Intake
- `select-template-root`: Select Template Root
- `create-template-structure`: Create Template Structure
- `write-manifest`: Write Manifest
- `write-example-files`: Write Example Files
- `register-template`: Register Template
- `run-template-doctor`: Run Template Doctor
- `handoff`: Handoff

## Artifacts

- `template-authoring-inputs`: Template Authoring Inputs
- `template-manifest`: Template Manifest
- `template-ready-handoff`: Template Ready Handoff
- `template-root-selection`: Template Root Selection
- `template-structure`: Template Structure
- `template-examples`: Template Examples
- `template-registry-entry`: Template Registry Entry
- `template-doctor-report`: Template Doctor Report

## Gates and acceptance criteria

Run `python bin/pf.py process-doctor --project-root . --process reusable-template-authoring --contract-only` before treating a changed process as valid.

## Error handling

`none`

## Handoff / transition behavior

See `stage_completion`, `run_completion`, and `process_transitions` in the process YAML.

## Example run

`python bin/pf.py process-describe --project-root . --process reusable-template-authoring`

## CLI checks

`python bin/pf.py builtin-process-catalog-doctor --root . --public`

## What this process demonstrates

This process is a public stable built-in reference for the ProcessForge process catalog contract.
