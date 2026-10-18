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

- task_id: `docs111-tests`
- run_id: `docs-fix-1-1-1-shell-20260907`
- assignment: `.pf/assignments/docs111-tests.yaml`
- capsule: `.pf/contexts/assignment-capsules/docs111-tests.capsule.yaml`
- workspace_access_file: `.pf/runtime/agent-runs/docs-fix-1-1-1-shell-20260907/docs111-tests/workspace-access.json`
- worker_may_rebuild_context: `false`

## workspace_access

- knowledge_resources: `0`
- templates: `0`
- tools: `0`
- mcp: `0`

## allowed_files

- `tools/smoke_docs_current_code_contract.py`
- `tools/smoke_docs_agent_no_manual_infra.py`
- `tools/smoke_context_freshness_vs_execution_readiness.py`
- `.pf/artifacts/docs-fix-1.1.1-20260907/docs111-tests-report.md`

## allowed_read_files

- `docs/**`
- `prompts/**`
- `templates/**`
- `tools/**`
- `src/**`
- `updates/migrations/**`
- `.pf/contexts/project-context.snapshot.yaml`
- `.pf/artifacts/docs-audit-1.1.1-report-20260907.md`
- `.pf/artifacts/docs-audit-1.1.1-evidence/**`
- `.pf/artifacts/docs-fix-1.1.1-20260907/**`

## forbidden_files

- `VERSION`
- `CHANGELOG.md`
- `checksums/**`
- `tools/processforge.py`
- `src/**`
- `.pf/process-forge.yaml`

## required_outputs

- `docs111-tests-report` -> `.pf/artifacts/docs-fix-1.1.1-20260907/docs111-tests-report.md`

## expected_report

- `.pf/artifacts/docs-fix-1.1.1-20260907/docs111-tests-report.md`

## subagent_policy

- allow: `false`
- max_subagents: `0`
- require_reports: `false`
- reports_dir: ``
