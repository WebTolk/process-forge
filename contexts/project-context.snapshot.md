# Project Context Snapshot

## Generated

- generated_at: 2026-07-14T04:33:32Z
- valid_until: 2026-07-21T04:33:32Z

## Freshness

fresh

## Project

- id: process-forge
- name: ProcessForge

## Flow Root

`./`

## Connected Knowledge Packages

- processforge.core

## Enabled Processes

- software-feature-development
- bug-fix
- testing
- content-production
- knowledge-package-improvement
- process-version-upgrade
- workplace-initialization
- project-initialization
- session-bootstrap
- context-resolution

## Required Capabilities

- markdown_editing (available, info)
- repository_read (available, info)
- schema_validation (available, info)

## Optional Capabilities

- browser_verification (missing, warn)
- official_documentation_lookup (missing, warn)
- repository_symbol_analysis (missing, warn)

## Missing Tools / MCP

- None recorded in this snapshot.

## Hard Policies

- public.no_local_absolute_paths
- files.one_writer_per_scope
- secrets.do_not_store
- runtime.private
- markdown.not_machine_merge_source

## Preferences

- templates.project_overrides_global
- session.prefer_project_context_snapshot

## Templates

- templates/adr-template.md
- templates/artifact-template.md
- templates/assignment-front-matter-template.md
- templates/assignment-template.md
- templates/context-capsule-template.yaml
- templates/context-conflict-report-template.md
- templates/context-index-template.yaml
- templates/execution-context-package-template.yaml
- templates/execution-context-prompt-template.md
- templates/global-agents-processforge-section.md
- templates/global-resource-matching-report-template.md
- templates/handoff-template.md
- templates/package-manifest-template.yaml
- templates/process-definition-template.yaml
- templates/process-forge.local.yaml
- templates/process-forge.yaml
- templates/process-upgrade-assessment-template.md
- templates/project-agents-template.md
- templates/project-context.snapshot.md
- templates/project-context.snapshot.yaml
- templates/project-conventions-template.md
- templates/project-init-proposal-template.md
- templates/project-init-review-template.md
- templates/project-init.answers.yaml
- templates/project-profile-template.md
- templates/registries/knowledge-roots.yaml
- templates/registries/mcp.yaml
- templates/registries/package-roots.yaml
- templates/registries/platforms.yaml
- templates/registries/templates.yaml
- templates/registries/tools.yaml
- templates/repository-map-template.md
- templates/resolved-rules-template.yaml
- templates/reusable-template-template.yaml
- templates/review-template.md
- templates/session-metadata-template.yaml
- templates/session-start-template.yaml
- templates/session-status-report-template.md
- templates/terms.yaml
- templates/validation-report-template.md
- templates/workplace-init.answers.yaml
- templates/workplace.yaml

## Session Start

Read in this order:

1. `.pf/AGENTS.md` or legacy `AGENTS.md`.
2. `.pf/process-forge.yaml` or legacy `process-forge.yaml`.
3. this snapshot.
4. current assignment.
5. relevant logs/reviews/handoffs.

## Current Risks

- Markdown files are human-readable context and are not authoritative structured merge sources.
- If freshness is stale, refresh before using required capability decisions.

## Refresh Instructions

Run `python tools/processforge.py project-context-refresh --project-root <project-root>`.
