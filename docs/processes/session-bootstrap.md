# Session Bootstrap

## Purpose

Start or inspect a primary agent session by resolving session mode, current project context, and status report inputs.

## When to use

Use this built-in process when its stated purpose matches the assignment.

## Execution mode

`single_agent`

## Coordination requirements

`simple_allowed`

## Roles and responsibilities

Roles are declared in `processes/session-bootstrap.yaml`; responsibility boundaries separate operator, primary agent, Director, Inspector, worker, and CLI tool duties.

## Stages

- `intake`: Capture the Session Start Request or derive it from a short prompt.
- `mode-detection`: Classify the session as resume, project_init, assignment_execute, context_resolve, context_compile, or doctor_context.
- `flow-location`: Locate project AGENTS.md, process-forge.yaml, and optional local config.
- `workplace-resolution`: Resolve workplace references and available registries.
- `context-freshness-check`: Check context index, cache, and execution context fingerprints.
- `status-scan`: Read assignments, artifacts, reviews, handoffs, ADRs, logs, and validation reports relevant to the session.
- `session-report`: Produce the session status report or hand off to the next mode.

## Artifacts

- `session-start-request`: Session Start Request
- `session-status-report`: Session Status Report
- `session-mode-decision`: Session Mode Decision
- `flow-location-report`: Flow Location Report
- `workplace-resolution-report`: Workplace Resolution Report
- `context-freshness-report`: Context Freshness Report
- `session-status-inputs`: Session Status Inputs

## Gates and acceptance criteria

Run `python bin/pf.py process-doctor --project-root . --process session-bootstrap --contract-only` before treating a changed process as valid.

## Error handling

`none`

## Handoff / transition behavior

See `stage_completion`, `run_completion`, and `process_transitions` in the process YAML.

## Example run

`python bin/pf.py process-describe --project-root . --process session-bootstrap`

## CLI checks

`python bin/pf.py builtin-process-catalog-doctor --root . --public`

## What this process demonstrates

This process is a public stable built-in reference for the ProcessForge process catalog contract.
