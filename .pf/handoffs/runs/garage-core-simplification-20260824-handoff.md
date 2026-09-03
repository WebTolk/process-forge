# Handoff: implementation -> maintainer

Objective:
Garage Core Reset: make project context, search, and resolve usable before
hooks/session/daemon, while preserving Forge session telemetry as an enhancement.

Current status:
Completed with conditions. Local stdio MCP proof passed; hosted Codex MCP
schema/session proof remains a follow-up.

Input artifacts:
.pf/artifacts/garage-core-simplification/garage-simplification-current-state-audit.md
.pf/artifacts/garage-core-simplification/mcp-prerequisite-audit.md
.pf/artifacts/garage-core-simplification/garage-core-contract.md
.pf/artifacts/garage-core-simplification/garage-simplification-implementation-report.md
.pf/artifacts/garage-core-simplification/final-validation.md
.pf/runs/garage-core-simplification-20260824/summary.md

Files changed:
src/processforge_core/garage.py
tools/pf_runtime/mcp_server.py
tools/pf_runtime/host.py
tools/processforge.py
tools/smoke_garage_no_hooks_sessionless.py
tools/smoke_garage_session_enhanced.py
tools/smoke_garage_cross_project_security.py
tools/smoke_garage_real_joomla_search.py
docs/concepts/runtime-mcp.md
docs/concepts/resource-search-index.md
docs/concepts/garage-core.md
.pf/START_AGENT_HERE.md

Files not to touch:
dist/**
.pf/runtime/**

Known issues:
Hosted Codex MCP acceptance was not executed in this run. Do not represent the
local stdio proof as external host proof.

Required checks:
Repeat the targeted Garage release-test smoke set and run hosted Codex MCP
schema reload acceptance before claiming external host readiness.

Next recommended action:
Open a fresh Codex-hosted MCP session against this checkout and confirm
`pf.context -> pf.search -> pf.resolve` behavior from the host.
