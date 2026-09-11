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

- task_id: `f1011-search`
- run_id: `core-f09-f12-shell-20260910`
- assignment: `.pf/assignments/f1011-search.yaml`
- capsule: `.pf/contexts/assignment-capsules/f1011-search.capsule.yaml`
- workspace_access_file: `.pf/runtime/agent-runs/core-f09-f12-shell-20260910/f1011-search/workspace-access.json`
- worker_may_rebuild_context: `false`

## workspace_access

- knowledge_resources: `0`
- templates: `0`
- tools: `0`
- mcp: `0`

## allowed_files

- `src/processforge_core/local_resource_search.py`
- `tools/smoke_search_source_integrity.py`
- `.pf/artifacts/core-f09-f12-20260910/f1011-search/**`
- `.pf/tmp/f1011-search/**`

## allowed_read_files

- `src/processforge_core/core_update.py`
- `src/processforge_core/local_resource_search.py`
- `tools/pf_runtime/raw_ingress_kernel.py`
- `tools/smoke_*.py`
- `docs/**`
- `.pf/artifacts/python-core-audit-20260908/**`
- `.pf/artifacts/core-f09-f12-20260910/**`

## forbidden_files

- `VERSION`
- `CHANGELOG.md`
- `checksums/**`
- `tools/processforge.py`
- `.pf/process-forge.yaml`
- `.pf/artifacts/python-core-audit-20260908/**`

## required_outputs

- `f1011-search-report` -> `.pf/artifacts/core-f09-f12-20260910/f1011-search/report.md`

## expected_report

- `.pf/artifacts/core-f09-f12-20260910/f1011-search/report.md`

## subagent_policy

- allow: `false`
- max_subagents: `0`
- require_reports: `false`
- reports_dir: ``
