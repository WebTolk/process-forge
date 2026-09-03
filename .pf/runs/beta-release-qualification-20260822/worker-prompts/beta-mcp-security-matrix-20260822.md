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

- task_id: `beta-mcp-security-matrix-20260822`
- run_id: `beta-release-qualification-20260822`
- assignment: `.pf/assignments/beta-mcp-security-matrix-20260822.yaml`
- capsule: `.pf/contexts/assignment-capsules/beta-mcp-security-matrix-20260822.capsule.yaml`
- workspace_access_file: `.pf/runtime/agent-runs/beta-release-qualification-20260822/beta-mcp-security-matrix-20260822/workspace-access.json`
- worker_may_rebuild_context: `false`

## workspace_access

- knowledge_resources: `0`
- templates: `0`
- tools: `0`
- mcp: `0`

## allowed_files

- `.pf/reviews/beta-mcp-security-matrix-20260822.md`

## allowed_read_files

- `tools/pf_runtime/mcp_server.py`
- `tools/pf_runtime/session_read.py`
- `src/processforge_core/local_resource_search.py`
- `src/processforge_core/project_initialization.py`
- `.pf/artifacts/beta-release-qualification-20260822/orchestrator-plan.md`

## forbidden_files


## required_outputs


## expected_report

- `.pf/reviews/beta-mcp-security-matrix-20260822.md`

## subagent_policy

- allow: `false`
- max_subagents: `0`
- require_reports: `false`
- reports_dir: ``
