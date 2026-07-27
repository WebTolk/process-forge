# Guided Workplace Setup

## Purpose

Agent-guided dialogue for preparing a ProcessForge workplace, reviewing a proposal, applying workplace files, and producing project-onboarding next steps.

## When to use

Use this built-in process when its stated purpose matches the assignment.

## Execution mode

`single_agent`

## Coordination requirements

`organized_optional`

## Roles and responsibilities

Roles are declared in `processes/guided-workplace-setup.yaml`; responsibility boundaries separate operator, primary agent, Director, Inspector, worker, and CLI tool duties.

## Stages

- `intake`: Create setup session artifacts and seed answers.
- `dialogue`: Ask block-scoped questions including Director capability, default project mode, Director Office initialization, and update answers YAML after each block.
- `review`: Check privacy, resource, and platform-neutrality policy before apply.
- `apply`: Delegate to workplace-init internals, run doctor-workplace, and write agent instruction snippets.

## Artifacts

- `answers`: Guided Workplace Answers
- `proposal`: Guided Workplace Proposal
- `review`: Guided Workplace Review
- `apply-report`: Guided Workplace Apply Report
- `agent-instructions`: Agent Instruction Snippet
- `next-steps`: Project Onboarding Next Steps

## Gates and acceptance criteria

Run `python bin/pf.py process-doctor --project-root . --process guided-workplace-setup --contract-only` before treating a changed process as valid.

## Error handling

`needs_operator`

## Handoff / transition behavior

See `stage_completion`, `run_completion`, and `process_transitions` in the process YAML.

## Example run

`python bin/pf.py process-describe --project-root . --process guided-workplace-setup`

## CLI checks

`python bin/pf.py builtin-process-catalog-doctor --root . --public`

## What this process demonstrates

This process is a public stable built-in reference for the ProcessForge process catalog contract.
