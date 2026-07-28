# Documentation Mirror Import

## Purpose

Plan documentation mirror imports and resource indexes without crawling large documentation by default.

## When to use

Use this built-in process when its stated purpose matches the assignment.

## Execution mode

`single_agent`

## Coordination requirements

`simple_allowed`

## Roles and responsibilities

Roles are declared in `processes/core/documentation-mirror-import.yaml`; responsibility boundaries separate operator, primary agent, Director, Inspector, worker, and CLI tool duties.

## Stages

- `intake`: Capture source, topics, target package, and import intent.
- `mirror-plan`: Create license assessment, mirror plan, and resource index plan without downloading content.

## Artifacts

- `documentation-import-request`: Documentation Import Request
- `mirror-plan`: Mirror Plan
- `source-register`: Source Register
- `license-assessment`: License Assessment
- `resource-index`: Resource Index

## Gates and acceptance criteria

Run `python bin/pf.py process-doctor --project-root . --process documentation-mirror-import --contract-only` before treating a changed process as valid.

## Error handling

`none`

## Handoff / transition behavior

See `stage_completion`, `run_completion`, and `process_transitions` in the process YAML.

## Example run

`python bin/pf.py process-describe --project-root . --process documentation-mirror-import`

## CLI checks

`python bin/pf.py builtin-process-catalog-doctor --root . --public`

## What this process demonstrates

This process is a public stable built-in reference for the ProcessForge process catalog contract.
