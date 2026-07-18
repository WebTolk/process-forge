# Project Context Snapshot

## Generated

- generated_at: 2026-07-18T09:32:10Z
- valid_until: 2026-07-25T09:32:10Z

## Freshness

fresh

## Project

- id: process-forge
- name: ProcessForge

## Flow Root

`.pf/`

## Linked ProcessForge

- version: 0.1.0-rc.1
- constraint: ^0.1
- install_mode: linked
- distribution: processforge (available)

## Connected Knowledge Packages

- processforge.core
- project.process-forge

## Platform Contracts

- None.

## Required Knowledge Resources

- None.

## Recommended Knowledge Resources

- None.

## Enabled Processes

- software-feature-development
- bug-fix
- testing
- content-production
- knowledge-package-improvement
- process-version-upgrade
- workplace-initialization
- project-onboarding
- project-initialization
- session-bootstrap
- context-resolution
- processforge-update-check
- knowledge-resource-add
- documentation-mirror-import
- knowledge-package-update
- template-add
- tool-register
- mcp-register
- platform-contract-install
- process-template-install
- reusable-template-authoring
- knowledge-package-authoring
- platform-contract-authoring
- process-authoring
- authoring-parity-audit
- task-batch-execution

## Required Capabilities

- markdown_editing (available, info)
- repository_read (available, info)
- schema_validation (available, info)

## Optional Capabilities

- browser_verification (missing, warn)
- official_documentation_lookup (missing, warn)
- repository_symbol_analysis (missing, warn)

## Required Tools

- None.

## Recommended Tools

- None.

## Required MCP

- None.

## Recommended MCP

- None.

## Hard Policies

- public.no_local_absolute_paths
- files.one_writer_per_scope
- secrets.do_not_store
- runtime.private
- markdown.not_machine_merge_source

## Preferences

- templates.project_overrides_global
- session.prefer_project_context_snapshot

## Project Templates

- None.

## Required Templates

- None.

## Recommended Templates

- None.

## Session Start

Read in this order:

1. `.pf/AGENTS.md`.
2. `.pf/process-forge.yaml`.
3. this snapshot.
4. current assignment.
5. relevant logs/reviews/handoffs.

Telemetry root: `.pf/runtime/telemetry`
Events log: `.pf/runtime/events/events.ndjson`

## Current Risks

- Markdown files are human-readable context and are not authoritative structured merge sources.
- If freshness is stale, refresh before using required capability decisions.

## Refresh Instructions

Run `python bin/pf.py project-context-refresh --project-root <project-root>` from the ProcessForge distribution root, or `python .pf/runtime/bin/pf.py project-context-refresh --project-root .` inside the linked project.
