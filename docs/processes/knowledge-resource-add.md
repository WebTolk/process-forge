# Knowledge Resource Add

## Purpose

Add a knowledge resource through proposal, classification, package update, index refresh, validation, and review.

## When to use

Use this built-in process when its stated purpose matches the assignment.

## Execution mode

`single_agent`

## Coordination requirements

`simple_allowed`

## Roles and responsibilities

Roles are declared in `processes/core/knowledge-resource-add.yaml`; responsibility boundaries separate operator, primary agent, Director, Inspector, worker, and CLI tool duties.

## Stages

- `intake`: Capture the resource request and target package.
- `target-resolution`: Resolve package, resource kind, path_ref, source, license, and load_policy.
- `package-index-update`: Update package manifest and resource index without loading heavy content.
- `validation`: Run package doctor and public cleanliness checks.

## Artifacts

- `knowledge-resource-add-request`: Knowledge Resource Add Request
- `resource-record`: Resource Record
- `package-index-update`: Package Index Update
- `target-resolution-report`: Target Resolution Report
- `source-note`: Source Note
- `license-note`: License Note
- `validation-report`: Validation Report
- `review`: Review

## Gates and acceptance criteria

Run `python bin/pf.py process-doctor --project-root . --process knowledge-resource-add --contract-only` before treating a changed process as valid.

## Error handling

`none`

## Handoff / transition behavior

See `stage_completion`, `run_completion`, and `process_transitions` in the process YAML.

## Example run

`python bin/pf.py process-describe --project-root . --process knowledge-resource-add`

## CLI checks

`python bin/pf.py builtin-process-catalog-doctor --root . --public`

## What this process demonstrates

This process is a public stable built-in reference for the ProcessForge process catalog contract.
