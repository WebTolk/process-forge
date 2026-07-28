# Knowledge Package Authoring

## Purpose

Create a workplace knowledge package through authoritative package roots.

## When to use

Use this built-in process when its stated purpose matches the assignment.

## Execution mode

`single_agent`

## Coordination requirements

`simple_allowed`

## Roles and responsibilities

Roles are declared in `processes/core/knowledge-package-authoring.yaml`; responsibility boundaries separate operator, primary agent, Director, Inspector, worker, and CLI tool duties.

## Stages

- `intake`: Intake
- `select-package-root`: Select Package Root
- `create-package-structure`: Create Package Structure
- `write-package-manifest`: Write Package Manifest
- `create-resource-index`: Create Resource Index
- `add-initial-resources`: Add Initial Resources
- `run-package-doctor`: Run Package Doctor
- `handoff`: Handoff

## Artifacts

- `package-manifest`: Package Manifest
- `resource-index`: Resource Index
- `knowledge-package-ready-handoff`: Knowledge Package Ready Handoff
- `knowledge-package-inputs`: Knowledge Package Inputs
- `package-root-selection`: Package Root Selection
- `package-structure`: Package Structure
- `initial-resources`: Initial Resources
- `package-doctor-report`: Package Doctor Report

## Gates and acceptance criteria

Run `python bin/pf.py process-doctor --project-root . --process knowledge-package-authoring --contract-only` before treating a changed process as valid.

## Error handling

`none`

## Handoff / transition behavior

See `stage_completion`, `run_completion`, and `process_transitions` in the process YAML.

## Example run

`python bin/pf.py process-describe --project-root . --process knowledge-package-authoring`

## CLI checks

`python bin/pf.py builtin-process-catalog-doctor --root . --public`

## What this process demonstrates

This process is a public stable built-in reference for the ProcessForge process catalog contract.
