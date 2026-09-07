# Project Context Snapshot

## Generated

- generated_at: 2026-09-03T12:39:43Z
- valid_until: 2026-09-10T12:39:43Z

## Freshness

fresh

## Project

- id: process-forge
- name: ProcessForge

## Flow Root

`.pf/`

## Linked ProcessForge

- version: 1.1.0
- constraint: ^1.0
- install_mode: linked
- distribution: processforge (available)

## Coordination Mode

- project_mode: inherit
- workplace_default_project_mode: simple
- effective_mode: simple
- director_available_at_workplace: false
- director_required: false

## Connected Knowledge Packages

- processforge.core
- project.process-forge

## Platform Contracts

- None.

## Platform Stack

- None.

## Selected Specializations

- None.

## Effective Resources

- docs.php (activated, None)
- docs.web.accessibility (activated, None)
- docs.web.css (activated, None)
- docs.web.html (activated, None)
- docs.web.javascript (activated, None)
- docs.web.performance (activated, None)

## Provided Capabilities

- architecture
- investigation
- process_coordination
- reporting
- repository_read
- repository_write
- review
- test_execution
- test_planning
- test_running

## Execution Route

- process: None.
- required_capabilities: None.
- required_evidence: None.

## Capability Resolution

- satisfied: 0
- unsatisfied: 0

## Applied Project Overrides

- None.

## Resolved Parameters

- namespaces: None.
- sources: 0
- conflicts: 0

## Resolution Conflicts

- None.

## Required Knowledge Resources

- project.process-forge:project-profile
- project.process-forge:project-artifacts

## Recommended Knowledge Resources

- None.

## Enabled Processes

- knowledge-package-improvement
- process-version-upgrade
- workplace-initialization
- project-onboarding
- project-initialization
- session-bootstrap
- context-resolution
- processforge-update-check
- knowledge-resource-add
- knowledge-package-update
- template-add
- tool-register
- mcp-register
- platform-contract-install
- reusable-template-authoring
- knowledge-package-authoring
- platform-contract-authoring
- process-authoring
- authoring-parity-audit
- task-batch-execution
- guided-workplace-setup
- multi-agent-task-orchestration
- runtime-driver-registry
- process-supervisor
- agent-director-supervision
- orchestrator-shell-agents-supervision

## Required Capabilities

- markdown_editing (available, info)
- repository_read (available, info)
- schema_validation (available, info)

## Optional Capabilities

- browser_verification (missing, warn)
- official_documentation_lookup (missing, warn)
- repository_symbol_analysis (available, info)

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
- secrets.public_exports_sanitized
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
