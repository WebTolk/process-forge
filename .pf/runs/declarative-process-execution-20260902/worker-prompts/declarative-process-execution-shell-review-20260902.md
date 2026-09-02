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

- task_id: `declarative-process-execution-shell-review-20260902`
- run_id: `declarative-process-execution-20260902`
- assignment: `.pf/assignments/declarative-process-execution-shell-review-20260902.yaml`
- capsule: `.pf/contexts/assignment-capsules/declarative-process-execution-shell-review-20260902.capsule.yaml`
- workspace_access_file: `.pf/runtime/agent-runs/declarative-process-execution-20260902/declarative-process-execution-shell-review-20260902/workspace-access.json`
- worker_may_rebuild_context: `false`

## workspace_access

- knowledge_resources: `0`
- templates: `0`
- tools: `0`
- mcp: `0`

## allowed_files

- `.pf/reviews/declarative-process-execution-shell-agent.md`

## allowed_read_files

- `задания/process-forge-declarative-process-execution-master-prompt.md`
- `src/processforge_core/process_execution.py`
- `src/processforge_core/garage.py`
- `tools/pf_runtime/mcp_server.py`
- `tools/pf_runtime/host.py`
- `tools/processforge.py`
- `schemas/process-definition.schema.json`
- `schemas/process-event.schema.json`
- `tools/process_execution_smoke_support.py`
- `tools/smoke_work_transition_*.py`
- `tools/smoke_work_start_no_stage_guessing.py`

## forbidden_files


## required_outputs

- `shell-agent-review` -> `.pf/reviews/declarative-process-execution-shell-agent.md`

## expected_report

- `.pf/reviews/declarative-process-execution-shell-agent.md`

## subagent_policy

- allow: `false`
- max_subagents: `0`
- require_reports: `false`
- reports_dir: ``
