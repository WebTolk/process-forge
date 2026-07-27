# Context Resolution

## Purpose

Resolve ProcessForge sources into context index, rules, conflict report, and assignment context packages.

## When to use

Use this built-in process when its stated purpose matches the assignment.

## Execution mode

`single_agent`

## Coordination requirements

`simple_allowed`

## Roles and responsibilities

Roles are declared in `processes/context-resolution.yaml`; responsibility boundaries separate operator, primary agent, Director, Inspector, worker, and CLI tool duties.

## Stages

- `source-discovery`: Discover required workplace, project, process, package, template, and assignment sources.
- `rule-classification`: Classify rules as hard, locked, preference, gate, tool, or template.
- `cascade-merge`: Merge rules in the configured cascade order without weakening locked hard policies.
- `conflict-detection`: Detect blocked, warn, requires_approval, and resolved outcomes.
- `context-index-generation`: Write source list, checksums, selected packages, templates, tools, and capabilities.
- `resolved-rules-generation`: Write resolved rules grouped by classification.
- `fingerprint-recording`: Record source fingerprints for cache and freshness checks.
- `ecp-capsule-generation`: Compile assignment-specific ECP and optional context capsule.

## Artifacts

- `context-index`: Context Index
- `resolved-rules`: Resolved Rules
- `context-conflict-report`: Context Conflict Report
- `context-cache`: Context Cache
- `context-capsule`: Context Capsule
- `source-inventory`: Source Inventory
- `classified-rules`: Classified Rules
- `execution-context-package`: Execution Context Package

## Gates and acceptance criteria

Run `python bin/pf.py process-doctor --project-root . --process context-resolution --contract-only` before treating a changed process as valid.

## Error handling

`none`

## Handoff / transition behavior

See `stage_completion`, `run_completion`, and `process_transitions` in the process YAML.

## Example run

`python bin/pf.py process-describe --project-root . --process context-resolution`

## CLI checks

`python bin/pf.py builtin-process-catalog-doctor --root . --public`

## What this process demonstrates

This process is a public stable built-in reference for the ProcessForge process catalog contract.
