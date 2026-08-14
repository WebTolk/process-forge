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

- task_id: `python-core-process-contract-inventory`
- run_id: `python-core-refactor-phase-a-20260814`
- assignment: `.pf/assignments/python-core-process-contract-inventory.yaml`
- capsule: `.pf/contexts/assignment-capsules/python-core-process-contract-inventory.capsule.yaml`
- workspace_access_file: `.pf/runtime/agent-runs/python-core-refactor-phase-a-20260814/python-core-process-contract-inventory/workspace-access.json`
- worker_may_rebuild_context: `false`

## workspace_access

- knowledge_resources: `0`
- templates: `0`
- tools: `0`
- mcp: `0`

## allowed_files


## allowed_read_files

- `.pf/AGENTS.md`
- `.pf/contexts/project-context.snapshot.yaml`
- `.pf/artifacts/process-stage-contract-normalization-20260814/**`
- `schemas/process-definition.schema.json`
- `processes/core/**`
- `packs/**`
- `tools/processforge.py`
- `tools/smoke_process*.py`
- `tools/validate-process-forge-schemas.py`

## forbidden_files

- `tools/pf_runtime/**`
- `bin/**`
- `docs/**`

## required_outputs

- `process-contract-inventory` -> `.pf/artifacts/python-core-refactor-phase-a-20260814/process-contract-inventory.md`

## expected_report

- `.pf/artifacts/python-core-refactor-phase-a-20260814/process-contract-inventory.md`

## subagent_policy

- allow: `false`
- max_subagents: `0`
- require_reports: `false`
- reports_dir: ``
