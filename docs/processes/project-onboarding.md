# Project Onboarding

## Purpose

Attach a project to an existing ProcessForge workplace without recreating the workplace.

## When to use

Use this built-in process when its stated purpose matches the assignment.

## Execution mode

`single_agent`

## Coordination requirements

`simple_allowed`

## Roles and responsibilities

Roles are declared in `processes/project-onboarding.yaml`; responsibility boundaries separate operator, primary agent, Director, Inspector, worker, and CLI tool duties.

## Stages

- `intake`: Capture project root, workplace root, project type, project coordination mode, and optional answers.
- `create-project-flow`: Create `.pf/`, public manifest, private local config, hooks config, and flow folders.
- `detect-project`: Detect project type, language markers, and platform contract requirements.
- `snapshot`: Refresh the project context snapshot after `.pf/` is created, including effective coordination mode.
- `first-assignment`: Create the initial verification assignment for the newly onboarded project.
- `validate`: Run doctor-project and record readable fix hints when checks fail.
- `handoff`: Create project ready handoff for the first assignment.

## Artifacts

- `project-onboarding-inputs`: Project Onboarding Inputs
- `project-flow-root`: Project Flow Root
- `project-context-snapshot`: Project Context Snapshot
- `first-assignment`: First Assignment
- `start-agent-here`: Start Agent Here
- `project-ready-handoff`: Project Ready Handoff
- `project-classification-report`: Project Classification Report
- `global-resource-matching-report`: Global Resource Matching Report
- `project-doctor-report`: Project Doctor Report

## Gates and acceptance criteria

Run `python bin/pf.py process-doctor --project-root . --process project-onboarding --contract-only` before treating a changed process as valid.

## Error handling

`none`

## Handoff / transition behavior

See `stage_completion`, `run_completion`, and `process_transitions` in the process YAML.

## Example run

`python bin/pf.py process-describe --project-root . --process project-onboarding`

## CLI checks

`python bin/pf.py builtin-process-catalog-doctor --root . --public`

## What this process demonstrates

This process is a public stable built-in reference for the ProcessForge process catalog contract.
