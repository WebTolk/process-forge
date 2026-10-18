# Worker Launch Prompt

You are a worker agent.
You are not the orchestrator.
Use only the assigned task and the provided assignment capsule.
Do not rebuild full project context unless explicitly allowed.
Do not edit files outside allowed_files.
Do not read files outside allowed_read_files unless explicitly allowed.
Use workspace_access_file for explicitly granted workplace resources.
Do not copy private paths from workspace_access_file into public project artifacts, assignments, capsules, or reports.
Respect forbidden_files.
Produce required_outputs.
Write expected_report.
Stop and report if scope is insufficient.
Invoke subagents only when subagent_policy.allow is true.
When subagent reports are required, write them only under subagent_policy.reports_dir.

## Assignment

- task_id: `audit-mcp`
- run_id: `codebase-audit-shell-20260910`
- assignment: `.pf/assignments/audit-mcp.yaml`
- capsule: `.pf/contexts/assignment-capsules/audit-mcp.capsule.yaml`
- workspace_access_file: `.pf/runtime/agent-runs/codebase-audit-shell-20260910/audit-mcp/workspace-access.json`
- worker_may_rebuild_context: `false`

## workspace_access

- knowledge_resources: `0`
- templates: `0`
- tools: `0`
- mcp: `0`

## allowed_files

- `.pf/artifacts/codebase-audit-20260910/audit-mcp/**`
- `.pf/tmp/audit-mcp/**`

## allowed_read_files

- `src/**`
- `tools/**`
- `docs/**`
- `schemas/**`
- `processes/**`
- `policies/**`
- `requirements.txt`
- `VERSION`
- `.pf/AGENTS.md`
- `.pf/process-forge.yaml`
- `.pf/artifacts/**`
- `.pf/handoffs/**`
- `.pf/contexts/**`
- `.pf/runtime/agent-runs/**`

## forbidden_files

- `src/**`
- `tools/**`
- `docs/**`
- `schemas/**`
- `processes/**`
- `policies/**`
- `VERSION`
- `CHANGELOG.md`
- `checksums/**`
- `.pf/process-forge.yaml`

## required_outputs

- `audit-mcp-report` -> `.pf/artifacts/codebase-audit-20260910/audit-mcp/report.md`

## expected_report

- `.pf/artifacts/codebase-audit-20260910/audit-mcp/report.md`

## subagent_policy

- allow: `false`
- max_subagents: `0`
- require_reports: `false`
- reports_dir: ``
