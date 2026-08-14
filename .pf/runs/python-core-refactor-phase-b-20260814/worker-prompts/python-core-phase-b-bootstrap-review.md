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

- task_id: `python-core-phase-b-bootstrap-review`
- run_id: `python-core-refactor-phase-b-20260814`
- assignment: `.pf/assignments/python-core-phase-b-bootstrap-review.yaml`
- capsule: `.pf/contexts/assignment-capsules/python-core-phase-b-bootstrap-review.capsule.yaml`
- workspace_access_file: `.pf/runtime/agent-runs/python-core-refactor-phase-b-20260814/python-core-phase-b-bootstrap-review/workspace-access.json`
- worker_may_rebuild_context: `false`

## workspace_access

- knowledge_resources: `0`
- templates: `0`
- tools: `0`
- mcp: `0`

## allowed_files


## allowed_read_files

- `.pf/AGENTS.md`
- `.pf/artifacts/python-core-refactor-phase-b-20260814/package-bootstrap-spec.md`
- `.pf/artifacts/python-core-refactor-phase-b-20260814/package-bootstrap-spec-review.md`
- `.pf/artifacts/python-core-refactor-phase-b-20260814/bootstrap-baseline.md`
- `.pf/artifacts/python-core-refactor-phase-b-20260814/package-bootstrap-patch.md`
- `src/processforge_core/__init__.py`
- `src/processforge_core/bootstrap.py`
- `tools/pf_runtime/mcp_server.py`
- `tools/pf_runtime/codex_hooks.py`
- `tools/smoke_processforge_core_package_bootstrap.py`
- `tools/processforge.py`
- `tools/pf_runtime/host.py`
- `tools/pf_runtime/service.py`
- `bin/pf.py`

## forbidden_files


## required_outputs

- `bootstrap-review` -> `.pf/artifacts/python-core-refactor-phase-b-20260814/package-bootstrap-review.md`

## expected_report

- `.pf/artifacts/python-core-refactor-phase-b-20260814/package-bootstrap-review.md`

## subagent_policy

- allow: `false`
- max_subagents: `0`
- require_reports: `false`
- reports_dir: ``
