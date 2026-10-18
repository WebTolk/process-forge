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

- task_id: `a11-hooks`
- run_id: `core-a01-a11-wave3-20260911`
- assignment: `.pf/assignments/a11-hooks.yaml`
- capsule: `.pf/contexts/assignment-capsules/a11-hooks.capsule.yaml`
- workspace_access_file: `.pf/runtime/agent-runs/core-a01-a11-wave3-20260911/a11-hooks/workspace-access.json`
- worker_may_rebuild_context: `false`

## workspace_access

- knowledge_resources: `0`
- templates: `0`
- tools: `0`
- mcp: `0`

## allowed_files

- `tools/pf_runtime/codex_hooks.py`
- `tools/smoke_codex_lifecycle_identity.py`
- `.pf/artifacts/core-a01-a11-20260911/a11-hooks/**`
- `.pf/tmp/a11-hooks/**`

## allowed_read_files

- `tools/pf_runtime/codex_hooks.py`
- `tools/smoke_codex_lifecycle_identity.py`
- `src/processforge_core/**`
- `tools/pf_runtime/**`
- `tools/processforge.py`
- `tools/*smoke*.py`
- `tools/*helpers*.py`
- `docs/concepts/**`
- `.pf/artifacts/core-a01-a11-20260911/**`
- `.pf/artifacts/codebase-audit-20260910/**`
- `.pf/AGENTS.md`
- `.pf/contexts/**`

## forbidden_files

- `VERSION`
- `CHANGELOG.md`
- `checksums/**`
- `.pf/artifacts/codebase-audit-20260910/**`
- `.pf/process-forge.yaml`

## required_outputs

- `a11-hooks-report` -> `.pf/artifacts/core-a01-a11-20260911/a11-hooks/report.md`

## expected_report

- `.pf/artifacts/core-a01-a11-20260911/a11-hooks/report.md`

## subagent_policy

- allow: `false`
- max_subagents: `0`
- require_reports: `false`
- reports_dir: ``
