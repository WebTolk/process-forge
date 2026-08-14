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

- task_id: `python-core-compatibility-inventory`
- run_id: `python-core-refactor-phase-a-20260814`
- assignment: `.pf/assignments/python-core-compatibility-inventory.yaml`
- capsule: `.pf/contexts/assignment-capsules/python-core-compatibility-inventory.capsule.yaml`
- workspace_access_file: `.pf/runtime/agent-runs/python-core-refactor-phase-a-20260814/python-core-compatibility-inventory/workspace-access.json`
- worker_may_rebuild_context: `false`

## workspace_access

- knowledge_resources: `0`
- templates: `0`
- tools: `0`
- mcp: `0`

## allowed_files


## allowed_read_files

- `.pf/AGENTS.md`
- `задания/process-forge-python-core-refactoring-master-prompt.md`
- `.pf/artifacts/python-core-refactor-phase-a-20260814/public-surface-inventory-redacted.md`
- `README.md`
- `README.ru.md`
- `QUICKSTART.md`
- `QUICKSTART.ru.md`
- `docs/**`
- `examples/**`
- `bin/pf.py`
- `tools/processforge.py`
- `tools/pf_runtime/**`
- `.processforge-releaseignore`

## forbidden_files


## required_outputs

- `python-core-compatibility-cleanup` -> `.pf/artifacts/python-core-refactor-phase-a-20260814/python-core-compatibility-cleanup.md`

## expected_report

- `.pf/artifacts/python-core-refactor-phase-a-20260814/python-core-compatibility-cleanup.md`

## subagent_policy

- allow: `false`
- max_subagents: `0`
- require_reports: `false`
- reports_dir: ``
