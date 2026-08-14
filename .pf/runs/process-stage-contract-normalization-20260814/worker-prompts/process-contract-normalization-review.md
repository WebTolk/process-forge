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

- task_id: `process-contract-normalization-review`
- run_id: `process-stage-contract-normalization-20260814`
- assignment: `.pf/assignments/process-contract-normalization-review.yaml`
- capsule: `.pf/contexts/assignment-capsules/process-contract-normalization-review.capsule.yaml`
- workspace_access_file: `.pf/runtime/agent-runs/process-stage-contract-normalization-20260814/process-contract-normalization-review/workspace-access.json`
- worker_may_rebuild_context: `false`

## workspace_access

- knowledge_resources: `0`
- templates: `0`
- tools: `0`
- mcp: `0`

## allowed_files

- `.pf/reviews/process-stage-contract-normalization-review.md`

## allowed_read_files

- `schemas/process-definition.schema.json`
- `schemas/process-transition.schema.json`
- `schemas/process-route-map.schema.json`
- `templates/process-definition-template.yaml`
- `processes/core/process-supervisor.yaml`
- `tools/processforge.py`
- `tools/pf_runtime/host.py`
- `docs/authoring/process-authoring.md`
- `tools/smoke_process_stage_contract_normalization.py`
- `.pf/artifacts/process-stage-contract-normalization-20260814/process-contract-normalization-audit.md`

## forbidden_files


## required_outputs

- `process-contract-normalization-review` -> `.pf/reviews/process-stage-contract-normalization-review.md`

## expected_report

- `.pf/reviews/process-stage-contract-normalization-review.md`

## subagent_policy

- allow: `false`
- max_subagents: `0`
- require_reports: `false`
- reports_dir: ``
