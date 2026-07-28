# ProcessForge Update Check

## Purpose

Check a linked ProcessForge distribution update index and produce a project assessment without automatic migration.

## When to use

Use this built-in process when its stated purpose matches the assignment.

## Execution mode

`single_agent`

## Coordination requirements

`simple_allowed`

## Roles and responsibilities

Roles are declared in `processes/core/processforge-update-check.yaml`; responsibility boundaries separate operator, primary agent, Director, Inspector, worker, and CLI tool duties.

## Stages

- `discover`: Resolve the project manifest, local config, workplace registry, and distribution update index.
- `assess`: Compare the current version with the selected channel and record migration impact.

## Artifacts

- `update-assessment`: ProcessForge update assessment

## Gates and acceptance criteria

Run `python bin/pf.py process-doctor --project-root . --process processforge-update-check --contract-only` before treating a changed process as valid.

## Error handling

`none`

## Handoff / transition behavior

See `stage_completion`, `run_completion`, and `process_transitions` in the process YAML.

## Example run

`python bin/pf.py process-describe --project-root . --process processforge-update-check`

## CLI checks

`python bin/pf.py builtin-process-catalog-doctor --root . --public`

## What this process demonstrates

This process is a public stable built-in reference for the ProcessForge process catalog contract.
