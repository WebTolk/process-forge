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

- task_id: `process-transition-route-inventory`
- run_id: `process-stage-contract-normalization-20260814`
- assignment: `.pf/assignments/process-transition-route-inventory.yaml`
- capsule: `.pf/contexts/assignment-capsules/process-transition-route-inventory.capsule.yaml`
- workspace_access_file: `.pf/runtime/agent-runs/process-stage-contract-normalization-20260814/process-transition-route-inventory/workspace-access.json`
- worker_may_rebuild_context: `false`

## workspace_access

- knowledge_resources: `0`
- templates: `0`
- tools: `0`
- mcp: `0`

## allowed_files

- `.pf/artifacts/process-stage-contract-normalization-20260814/process-transition-route-inventory.md`

## allowed_read_files

- `schemas/process-definition.schema.json`
- `schemas/process-transition.schema.json`
- `schemas/process-route-map.schema.json`
- `.pf/process-routes.yaml`
- `tools/processforge.py`
- `docs`

## forbidden_files


## required_outputs

- `process-transition-route-inventory` -> `.pf/artifacts/process-stage-contract-normalization-20260814/process-transition-route-inventory.md`

## expected_report

- `.pf/artifacts/process-stage-contract-normalization-20260814/process-transition-route-inventory.md`

## subagent_policy

- allow: `false`
- max_subagents: `0`
- require_reports: `false`
- reports_dir: ``
