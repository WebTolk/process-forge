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

- task_id: `subagent-release-auditor`
- run_id: `subagent-stabilization-audit`
- assignment: `.pf/assignments/subagent-release-auditor.yaml`
- capsule: `.pf/contexts/assignment-capsules/subagent-release-auditor.capsule.yaml`
- workspace_access_file: `.pf/runtime/agent-runs/subagent-stabilization-audit/subagent-release-auditor/workspace-access.json`
- worker_may_rebuild_context: `false`

## workspace_access

- knowledge_resources: `0`
- templates: `0`
- tools: `0`
- mcp: `0`

## allowed_files


## allowed_read_files

- `tools/smoke_resource_authoring_processes.py`
- `tools/validate-*.py`
- `tools/processforge.py`
- `.processforge-releaseignore`
- `docs/release-checklist.md`

## forbidden_files

- `dist/**`
- `.pf/runtime/**`

## required_outputs


## expected_report

- `.pf/artifacts/subagent-stabilization-audit/release-auditor-report.md`

## subagent_policy

- allow: `false`
- max_subagents: `0`
- require_reports: `false`
- reports_dir: ``
