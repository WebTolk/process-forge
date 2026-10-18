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

- task_id: `review-runtime-core`
- run_id: `core-a01-a11-review-20260911`
- assignment: `.pf/assignments/review-runtime-core.yaml`
- capsule: `.pf/contexts/assignment-capsules/review-runtime-core.capsule.yaml`
- workspace_access_file: `.pf/runtime/agent-runs/core-a01-a11-review-20260911/review-runtime-core/workspace-access.json`
- worker_may_rebuild_context: `false`

## workspace_access

- knowledge_resources: `0`
- templates: `0`
- tools: `0`
- mcp: `0`

## allowed_files

- `.pf/artifacts/core-a01-a11-20260911/review-runtime-core/**`
- `.pf/tmp/review-runtime-core/**`

## allowed_read_files

- `src/processforge_core/local_resource_search.py`
- `src/processforge_core/core_update.py`
- `tools/pf_runtime/service.py`
- `tools/smoke_runtime_scheduler_failure_isolation.py`
- `tools/smoke_runtime_singleton_orphan.py`
- `tools/smoke_search_file_root_containment.py`
- `tools/smoke_core_update_migration_sources.py`
- `tools/smoke_long_lived_runtime.py`
- `tools/smoke_domain_neutral_core_helpers.py`
- `tools/processforge_subprocess.py`
- `docs/concepts/**`
- `.pf/artifacts/core-a01-a11-20260911/**`
- `.pf/logs/core-a01-a11-20260911.md`
- `.pf/AGENTS.md`

## forbidden_files

- `VERSION`
- `CHANGELOG.md`
- `checksums/**`
- `.pf/artifacts/codebase-audit-20260910/**`
- `.pf/process-forge.yaml`

## required_outputs

- `review-runtime-core-report` -> `.pf/artifacts/core-a01-a11-20260911/review-runtime-core/report.md`

## expected_report

- `.pf/artifacts/core-a01-a11-20260911/review-runtime-core/report.md`

## subagent_policy

- allow: `false`
- max_subagents: `0`
- require_reports: `false`
- reports_dir: ``
