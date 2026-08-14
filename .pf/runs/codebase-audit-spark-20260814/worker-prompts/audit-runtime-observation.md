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

- task_id: `audit-runtime-observation`
- run_id: `codebase-audit-spark-20260814`
- assignment: `.pf/assignments/audit-runtime-observation.yaml`
- capsule: `.pf/contexts/assignment-capsules/audit-runtime-observation.capsule.yaml`
- workspace_access_file: `.pf/runtime/agent-runs/codebase-audit-spark-20260814/audit-runtime-observation/workspace-access.json`
- worker_may_rebuild_context: `false`

## workspace_access

- knowledge_resources: `0`
- templates: `0`
- tools: `0`
- mcp: `0`

## allowed_files

- `.pf/artifacts/codebase-audit-20260814/runtime-observation-report.md`

## allowed_read_files

- `tools/pf_runtime/**`
- `tools/codex_exec_worker.py`
- `tools/processforge.py`
- `tools/smoke_runtime_ledger_hooks_mcp.py`
- `tools/smoke_codex_exec_worker.py`
- `schemas/agent-run-state.schema.json`
- `schemas/pf-runtime-agent-event.schema.json`

## forbidden_files


## required_outputs

- `runtime-observation-report` -> `.pf/artifacts/codebase-audit-20260814/runtime-observation-report.md`

## expected_report

- `.pf/artifacts/codebase-audit-20260814/runtime-observation-report.md`

## subagent_policy

- allow: `false`
- max_subagents: `0`
- require_reports: `false`
- reports_dir: ``
