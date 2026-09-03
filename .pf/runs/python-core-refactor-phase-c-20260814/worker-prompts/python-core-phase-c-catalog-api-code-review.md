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

- task_id: `python-core-phase-c-catalog-api-code-review`
- run_id: `python-core-refactor-phase-c-20260814`
- assignment: `.pf/assignments/python-core-phase-c-catalog-api-code-review.yaml`
- capsule: `.pf/contexts/assignment-capsules/python-core-phase-c-catalog-api-code-review.capsule.yaml`
- workspace_access_file: `.pf/runtime/agent-runs/python-core-refactor-phase-c-20260814/python-core-phase-c-catalog-api-code-review/workspace-access.json`
- worker_may_rebuild_context: `false`

## workspace_access

- knowledge_resources: `0`
- templates: `0`
- tools: `0`
- mcp: `0`

## allowed_files

- `.pf/artifacts/python-core-refactor-phase-c-20260814/catalog-api-code-review.md`

## allowed_read_files

- `.pf/artifacts/python-core-refactor-phase-c-20260814/catalog-api-patch-correction.md`
- `.pf/artifacts/python-core-refactor-phase-c-20260814/catalog-api-review.md`
- `tools/processforge.py`
- `tools/pf_runtime/host.py`
- `src/processforge_core/bootstrap.py`
- `src/processforge_core/common/__init__.py`
- `src/processforge_core/common/ids.py`
- `src/processforge_core/common/paths.py`
- `src/processforge_core/common/yaml_io.py`
- `src/processforge_core/process_catalog/__init__.py`
- `src/processforge_core/process_catalog/models.py`
- `src/processforge_core/process_catalog/service.py`

## forbidden_files


## required_outputs

- `catalog-api-code-review` -> `.pf/artifacts/python-core-refactor-phase-c-20260814/catalog-api-code-review.md`

## expected_report

- `.pf/artifacts/python-core-refactor-phase-c-20260814/catalog-api-code-review.md`

## subagent_policy

- allow: `false`
- max_subagents: `0`
- require_reports: `false`
- reports_dir: ``
