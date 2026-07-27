# Agent Director Supervision

## Purpose

Coordinates organized projects, multiple agent sessions, and process runs through pending handoffs, agent availability, leases, target runs, and continuation capsules; delegates task execution checks to the Process Execution Inspector.

## When to use

Use this built-in process when its stated purpose matches the assignment.

## Execution mode

`process_factory`

## Coordination requirements

`organized_required`

## Roles and responsibilities

Roles are declared in `processes/agent-director-supervision.yaml`; responsibility boundaries separate operator, primary agent, Director, Inspector, worker, and CLI tool duties.

## Stages

- `inspect`: Inspect pending handoffs
- `assign`: Assign available agent
- `wait-or-return`: Wait or return

## Artifacts

- `director-tick-report`: Director tick report

## Gates and acceptance criteria

Run `python bin/pf.py process-doctor --project-root . --process agent-director-supervision --contract-only` before treating a changed process as valid.

## Error handling

`director_inbox`

## Handoff / transition behavior

See `stage_completion`, `run_completion`, and `process_transitions` in the process YAML.

## Example run

`python bin/pf.py process-describe --project-root . --process agent-director-supervision`

## CLI checks

`python bin/pf.py builtin-process-catalog-doctor --root . --public`

## What this process demonstrates

This process is a public stable built-in reference for the ProcessForge process catalog contract.
