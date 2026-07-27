# Process Version Upgrade

## Purpose

Assess and perform safe upgrades between process versions.

## When to use

Use this built-in process when its stated purpose matches the assignment.

## Execution mode

`single_agent`

## Coordination requirements

`simple_allowed`

## Roles and responsibilities

Roles are declared in `processes/process-version-upgrade.yaml`; responsibility boundaries separate operator, primary agent, Director, Inspector, worker, and CLI tool duties.

## Stages

- `compare`: Identify changed stages, gates, and artifacts.
- `decide`: Approve, migrate, or block the upgrade.

## Artifacts

- `upgrade-assessment`: Upgrade Assessment
- `upgrade-decision`: Upgrade Decision

## Gates and acceptance criteria

Run `python bin/pf.py process-doctor --project-root . --process process-version-upgrade --contract-only` before treating a changed process as valid.

## Error handling

`none`

## Handoff / transition behavior

See `stage_completion`, `run_completion`, and `process_transitions` in the process YAML.

## Example run

`python bin/pf.py process-describe --project-root . --process process-version-upgrade`

## CLI checks

`python bin/pf.py builtin-process-catalog-doctor --root . --public`

## What this process demonstrates

This process is a public stable built-in reference for the ProcessForge process catalog contract.
