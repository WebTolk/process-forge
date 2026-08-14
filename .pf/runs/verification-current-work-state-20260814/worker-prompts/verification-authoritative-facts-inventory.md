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

- task_id: `verification-authoritative-facts-inventory`
- run_id: `verification-current-work-state-20260814`
- assignment: `.pf/assignments/verification-authoritative-facts-inventory.yaml`
- capsule: `.pf/contexts/assignment-capsules/verification-authoritative-facts-inventory.capsule.yaml`
- workspace_access_file: `.pf/runtime/agent-runs/verification-current-work-state-20260814/verification-authoritative-facts-inventory/workspace-access.json`
- worker_may_rebuild_context: `false`

## workspace_access

- knowledge_resources: `0`
- templates: `0`
- tools: `0`
- mcp: `0`

## allowed_files

- `.pf/artifacts/verification-current-work-state-20260814/authoritative-facts-inventory.md`

## allowed_read_files

- `задания/process-forge-verification-current-work-state-detailed-master-prompt.md`
- `.pf/AGENTS.md`
- `.pf/process-forge.yaml`
- `.pf/contexts/**`
- `.pf/assignments/**`
- `.pf/runs/**`
- `.pf/artifacts/**`
- `.pf/reviews/**`
- `.pf/handoffs/**`
- `processes/core/**`
- `schemas/**`
- `tools/processforge.py`
- `tools/pf_runtime/**`
- `tools/smoke_stage_projectors.py`
- `tools/smoke_runtime*.py`
- `tools/smoke_worker*.py`
- `docs/concepts/runtime-*.md`

## forbidden_files


## required_outputs

- `authoritative-facts-inventory` -> `.pf/artifacts/verification-current-work-state-20260814/authoritative-facts-inventory.md`

## expected_report

- `.pf/artifacts/verification-current-work-state-20260814/authoritative-facts-inventory.md`

## subagent_policy

- allow: `false`
- max_subagents: `0`
- require_reports: `false`
- reports_dir: ``
