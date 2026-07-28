# Project Initialization

## Purpose

Connect a project to ProcessForge and a configured workplace layer.

## When to use

Use this built-in process when its stated purpose matches the assignment.

## Execution mode

`single_agent`

## Coordination requirements

`simple_allowed`

## Roles and responsibilities

Roles are declared in `processes/core/project-initialization.yaml`; responsibility boundaries separate operator, primary agent, Director, Inspector, worker, and CLI tool duties.

## Stages

- `intake`: Capture project root, workplace manifest, and answers.
- `workplace-resolution`: Read workplace manifest and registries.
- `repository-scan`: Scan only the supplied project root.
- `project-classification`: Classify languages, platforms, frameworks, and project type.
- `global-resource-matching`: Match detected project needs against workplace registries.
- `project-specificity-extraction`: Create observed project conventions and project package draft.
- `proposal`: Produce project init proposal before applying changes.
- `review`: Review proposed project init changes.
- `apply`: Write project files without unsafe overwrite.
- `doctor`: Validate project init output.

## Artifacts

- `project-init-answers`: Project Init Answers
- `project-classification-report`: Project Classification Report
- `repository-map`: Repository Map
- `project-conventions`: Project Conventions
- `global-resource-matching-report`: Global Resource Matching Report
- `project-init-proposal`: Project Init Proposal
- `project-init-review`: Project Init Review
- `mcp-capability-report`: Mcp Capability Report
- `toolchain-detection-report`: Toolchain Detection Report
- `project-profile`: Project Profile
- `template-matching-report`: Template Matching Report
- `project-package-draft`: Project Package Draft
- `project-files`: Project Files
- `project-doctor-report`: Project Doctor Report

## Gates and acceptance criteria

Run `python bin/pf.py process-doctor --project-root . --process project-initialization --contract-only` before treating a changed process as valid.

## Error handling

`none`

## Handoff / transition behavior

See `stage_completion`, `run_completion`, and `process_transitions` in the process YAML.

## Example run

`python bin/pf.py process-describe --project-root . --process project-initialization`

## CLI checks

`python bin/pf.py builtin-process-catalog-doctor --root . --public`

## What this process demonstrates

This process is a public stable built-in reference for the ProcessForge process catalog contract.
