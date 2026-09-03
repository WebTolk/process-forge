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

- task_id: `harden-worker-run-shell-smoke`
- run_id: `worker-run-remediation-20260814`
- assignment: `.pf/assignments/harden-worker-run-shell-smoke.yaml`
- capsule: `.pf/contexts/assignment-capsules/harden-worker-run-shell-smoke.capsule.yaml`
- workspace_access_file: `.pf/runtime/agent-runs/worker-run-remediation-20260814/harden-worker-run-shell-smoke/workspace-access.json`
- worker_may_rebuild_context: `false`

## workspace_access

- knowledge_resources: `0`
- templates: `0`
- tools: `0`
- mcp: `0`

## allowed_files

- `tools/smoke_worker_run_shell.py`
- `.pf/artifacts/codebase-audit-20260814/harden-worker-run-shell-smoke-report.md`

## allowed_read_files

- `tools/smoke_worker_run_shell.py`
- `tools/processforge.py`
- `.pf/artifacts/codebase-audit-20260814/remediation-plan.md`

## forbidden_files


## required_outputs

- `harden-worker-run-shell-smoke-report` -> `.pf/artifacts/codebase-audit-20260814/harden-worker-run-shell-smoke-report.md`

## expected_report

- `.pf/artifacts/codebase-audit-20260814/harden-worker-run-shell-smoke-report.md`

## subagent_policy

- allow: `false`
- max_subagents: `0`
- require_reports: `false`
- reports_dir: ``
