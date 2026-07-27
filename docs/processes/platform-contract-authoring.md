# Platform Contract Authoring

## Purpose

Create a platform contract that links project type hints to packages, templates, tools, MCP, and processes.

## When to use

Use this built-in process when its stated purpose matches the assignment.

## Execution mode

`single_agent`

## Coordination requirements

`simple_allowed`

## Roles and responsibilities

Roles are declared in `processes/platform-contract-authoring.yaml`; responsibility boundaries separate operator, primary agent, Director, Inspector, worker, and CLI tool duties.

## Stages

- `intake`: Intake
- `select-platform-root`: Select Platform Root
- `create-platform-structure`: Create Platform Structure
- `write-platform-contract`: Write Platform Contract
- `link-capabilities`: Link Capabilities
- `link-knowledge-packages`: Link Knowledge Packages
- `link-templates`: Link Templates
- `link-tools-mcp`: Link Tools MCP
- `run-platform-doctor`: Run Platform Doctor
- `handoff`: Handoff

## Artifacts

- `platform-contract`: Platform Contract
- `platform-doctor-report`: Platform Doctor Report
- `platform-contract-ready-handoff`: Platform Contract Ready Handoff
- `platform-contract-inputs`: Platform Contract Inputs
- `platform-root-selection`: Platform Root Selection
- `platform-structure`: Platform Structure
- `capability-links`: Capability Links
- `knowledge-links`: Knowledge Links
- `template-links`: Template Links
- `tool-mcp-links`: Tool Mcp Links

## Gates and acceptance criteria

Run `python bin/pf.py process-doctor --project-root . --process platform-contract-authoring --contract-only` before treating a changed process as valid.

## Error handling

`none`

## Handoff / transition behavior

See `stage_completion`, `run_completion`, and `process_transitions` in the process YAML.

## Example run

`python bin/pf.py process-describe --project-root . --process platform-contract-authoring`

## CLI checks

`python bin/pf.py builtin-process-catalog-doctor --root . --public`

## What this process demonstrates

This process is a public stable built-in reference for the ProcessForge process catalog contract.
