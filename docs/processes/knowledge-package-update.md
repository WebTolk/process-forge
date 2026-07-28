# Knowledge Package Update

## Purpose

Update a knowledge package through current inspection, change proposal, resource/index update, compatibility check, and review.

## When to use

Use this built-in process when its stated purpose matches the assignment.

## Execution mode

`single_agent`

## Coordination requirements

`simple_allowed`

## Roles and responsibilities

Roles are declared in `processes/core/knowledge-package-update.yaml`; responsibility boundaries separate operator, primary agent, Director, Inspector, worker, and CLI tool duties.

## Stages

- `current-package-inspection`: Read package manifest and resource index metadata.
- `change-proposal`: Record resource, template, tool, or MCP changes before apply.
- `resource-update`: Apply accepted changes and refresh index.

## Artifacts

- `package-inspection-report`: Package Inspection Report
- `resource-index`: Resource Index
- `change-proposal`: Change Proposal
- `compatibility-check`: Compatibility Check
- `review`: Review

## Gates and acceptance criteria

Run `python bin/pf.py process-doctor --project-root . --process knowledge-package-update --contract-only` before treating a changed process as valid.

## Error handling

`none`

## Handoff / transition behavior

See `stage_completion`, `run_completion`, and `process_transitions` in the process YAML.

## Example run

`python bin/pf.py process-describe --project-root . --process knowledge-package-update`

## CLI checks

`python bin/pf.py builtin-process-catalog-doctor --root . --public`

## What this process demonstrates

This process is a public stable built-in reference for the ProcessForge process catalog contract.
