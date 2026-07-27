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

1. `.pf/AGENTS.md`
2. `.pf/process-forge.yaml`
3. this snapshot
4. current assignment
5. relevant logs/reviews/handoffs

Telemetry is written to `.pf/runtime/telemetry/`.
Flow events are written to `.pf/runtime/events/events.ndjson`.

## Current Risks

- Refresh before relying on required capability decisions when freshness is stale.

## Refresh Instructions

Run `python tools/processforge.py project-context-refresh --project-root <project-root>`.
