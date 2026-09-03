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

- task_id: `project-init-local-search-mcp-architecture-20260821`
- run_id: `project-init-local-search-mcp-20260821`
- assignment: `.pf/assignments/project-init-local-search-mcp-architecture-20260821.yaml`
- capsule: `.pf/contexts/assignment-capsules/project-init-local-search-mcp-architecture-20260821.capsule.yaml`
- workspace_access_file: `.pf/runtime/agent-runs/project-init-local-search-mcp-20260821/project-init-local-search-mcp-architecture-20260821/workspace-access.json`
- worker_may_rebuild_context: `false`

## workspace_access

- knowledge_resources: `0`
- templates: `0`
- tools: `0`
- mcp: `0`

## allowed_files

- `.pf/artifacts/project-init-local-search-mcp-20260821/project-initialization-current-state-audit.md`
- `.pf/artifacts/project-init-local-search-mcp-20260821/project-initialization-contract.md`
- `.pf/artifacts/project-init-local-search-mcp-20260821/local-resource-search-design.md`
- `.pf/artifacts/project-init-local-search-mcp-20260821/codex-mcp-tool-visibility-audit.md`
- `.pf/artifacts/project-init-local-search-mcp-20260821/workplace-mcp-surface-audit.md`
- `.pf/artifacts/project-init-local-search-mcp-20260821/workplace-console-design.md`
- `.pf/artifacts/project-init-local-search-mcp-20260821/mcp-patterns-for-processforge.md`

## allowed_read_files

- `.pf/AGENTS.md`
- `.pf/process-forge.yaml`
- `.pf/process-forge.local.yaml`
- `.pf/contexts/project-context.snapshot.yaml`
- `.pf/artifacts/project-init-local-search-mcp-20260821/project-initialization-current-state-audit-retry.md`
- `.pf/artifacts/project-init-local-search-mcp-20260821/sqlite-fts5-resource-inventory-retry.md`
- `tools/processforge.py`
- `tools/pf_runtime/mcp_server.py`
- `tools/pf_runtime/host.py`
- `tools/pf_runtime/session_read.py`
- `docs/authoring/project-initialization.md`
- `docs/processes/project-initialization.md`
- `docs/concepts/runtime-mcp.md`
- `docs/concepts/codex-session-read.md`
- `packs/official/software-development/processes/software-feature-development.yaml`

## forbidden_files


## required_outputs

- `project-initialization-current-state-audit` -> `.pf/artifacts/project-init-local-search-mcp-20260821/project-initialization-current-state-audit.md`
- `project-initialization-contract` -> `.pf/artifacts/project-init-local-search-mcp-20260821/project-initialization-contract.md`
- `local-resource-search-design` -> `.pf/artifacts/project-init-local-search-mcp-20260821/local-resource-search-design.md`
- `codex-mcp-tool-visibility-audit` -> `.pf/artifacts/project-init-local-search-mcp-20260821/codex-mcp-tool-visibility-audit.md`
- `workplace-mcp-surface-audit` -> `.pf/artifacts/project-init-local-search-mcp-20260821/workplace-mcp-surface-audit.md`
- `workplace-console-design` -> `.pf/artifacts/project-init-local-search-mcp-20260821/workplace-console-design.md`
- `mcp-patterns-for-processforge` -> `.pf/artifacts/project-init-local-search-mcp-20260821/mcp-patterns-for-processforge.md`

## expected_report

- `.pf/artifacts/project-init-local-search-mcp-20260821/project-initialization-contract.md`

## subagent_policy

- allow: `false`
- max_subagents: `0`
- require_reports: `false`
- reports_dir: ``
