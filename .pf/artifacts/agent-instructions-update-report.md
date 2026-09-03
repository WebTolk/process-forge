# Agent Instructions Update Report

Generated: 2026-08-24 14:00 +04

## Current Instruction Fit

The project-local `.pf/AGENTS.md` already contains the governing rules needed
for this stabilization:

- start from `.pf/process-forge.yaml`;
- identify the active assignment;
- use Execution Context Packages;
- check allowed/forbidden files before editing;
- save durable outputs;
- update `.pf/logs`;
- create review or handoff artifacts.

The developer-level instruction added one important operational guard:
repository analysis should use Serena or IDE MCP first, with shell fallback only
after that. This run followed that order; Serena was usable for targeted
pattern search, while broad project manifest searches were too noisy and were
replaced by focused shell reads.

## Update Decision

No project AGENTS file change was made in this slice. The observed invalid
stage problem is better addressed by a governed bootstrap API and by agent
behavior that reads actual process stages before creating tasks, not by adding
another static warning to AGENTS.

Status: `no_change_required`.
