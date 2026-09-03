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

- task_id: `implement-worker-run-lifecycle`
- run_id: `worker-run-remediation-20260814`
- assignment: `.pf/assignments/implement-worker-run-lifecycle.yaml`
- capsule: `.pf/contexts/assignment-capsules/implement-worker-run-lifecycle.capsule.yaml`
- workspace_access_file: `.pf/runtime/agent-runs/worker-run-remediation-20260814/implement-worker-run-lifecycle/workspace-access.json`
- worker_may_rebuild_context: `false`

## workspace_access

- knowledge_resources: `0`
- templates: `0`
- tools: `0`
- mcp: `0`

## allowed_files

- `tools/processforge.py`
- `.pf/artifacts/codebase-audit-20260814/implementation-lifecycle-worker-report.md`

## allowed_read_files

- `tools/processforge.py`
- `tools/smoke_worker_run_shell.py`
- `.pf/artifacts/codebase-audit-20260814/remediation-plan.md`
- `.pf/reviews/codebase-audit-remediation-plan-20260814-review.md`

## forbidden_files


## required_outputs

- `implementation-lifecycle-worker-report` -> `.pf/artifacts/codebase-audit-20260814/implementation-lifecycle-worker-report.md`

## expected_report

- `.pf/artifacts/codebase-audit-20260814/implementation-lifecycle-worker-report.md`

## subagent_policy

- allow: `false`
- max_subagents: `0`
- require_reports: `false`
- reports_dir: ``
