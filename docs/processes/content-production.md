# Content Production

## Purpose

Produce, review, and prepare content for publication.

## When to use

Use this built-in process when its stated purpose matches the assignment.

## Execution mode

`single_agent`

## Coordination requirements

`simple_allowed`

## Roles and responsibilities

Roles are declared in `processes/core/content-production.yaml`; responsibility boundaries separate operator, primary agent, Director, Inspector, worker, and CLI tool duties.

## Stages

- `brief`: Define audience, purpose, constraints, and sources.
- `draft`: Produce the first complete draft.
- `editorial-review`: Review accuracy, structure, and publication readiness.

## Artifacts

- `content-brief`: Content Brief
- `content-draft`: Content Draft
- `editorial-review`: Editorial Review
- `publication-handoff`: Publication Handoff

## Gates and acceptance criteria

Run `python bin/pf.py process-doctor --project-root . --process content-production --contract-only` before treating a changed process as valid.

## Error handling

`none`

## Evolve

`content-production` uses the common process-agnostic `evolve` block. It can
capture reusable editorial rules, content templates, terminology gaps, and
publication checks as local knowledge candidates. Sanitized export is required
before candidates leave the workplace queue.

Candidate targets are limited to `knowledge_package`, `template_package`, and
`project_rule`. Project voice and campaign-specific instructions stay narrow;
global style guidance needs explicit applicability before it can be promoted.

## Handoff / transition behavior

See `stage_completion`, `run_completion`, and `process_transitions` in the process YAML.

## Example run

`python bin/pf.py process-describe --project-root . --process content-production`

## CLI checks

`python bin/pf.py builtin-process-catalog-doctor --root . --public`

## What this process demonstrates

This process is a public stable built-in reference for the ProcessForge process catalog contract.
