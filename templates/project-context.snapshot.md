# Project Context Snapshot

## Generated

- generated_at:
- valid_until:

## Freshness

unknown

## Project

## Flow Root

`.pf/`

## Coordination Mode

- project_mode: inherit
- workplace_default_project_mode: simple
- effective_mode: simple
- director_available_at_workplace: false
- director_required: false

## Connected Knowledge Packages

- None.

## Enabled Processes

- None.

## Required Capabilities

- None.

## Optional Capabilities

- None.

## Missing Tools / MCP

- None.

## Hard Policies

- Public files must not contain local absolute paths.
- Runtime and telemetry are private.
- Markdown is not the stable machine merge source.

## Preferences

- Project templates override global templates when allowed.

## Templates

- None.

## Session Start

Read in this order:

1. root `AGENTS.md` (explicit `.pf/AGENTS.md` fallback in an unmigrated project)
2. `.pf/process-forge.yaml`
3. `pf.context`, or existing CLI `project-context-check` and verified context fallback
4. Run/assignment/immutable capsule returned by `pf.work.start`; retain those identities
5. required sources, resolved resources and relevant logs/reviews/handoffs
6. extended `.pf/AGENTS.md` instructions on demand

This snapshot records context; its presence alone does not establish freshness.
Use `pf.work.state` and `pf.work.transition` until `run_completed`; handle
`process_choice_required` from returned choices. START is optional guidance.
Manual session creation is an operator interface, not a prerequisite for work.
Explicit session telemetry lives in `.pf/runtime/telemetry/`, events in
`.pf/runtime/events/events.ndjson`.

## Current Risks

- Refresh before relying on required capability decisions when freshness is stale.

## Refresh Instructions

Run `python tools/processforge.py project-context-refresh --project-root <project-root>`.
